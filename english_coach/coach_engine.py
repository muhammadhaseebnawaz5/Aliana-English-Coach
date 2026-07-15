# english_coach/coach_engine.py - Main English Coach Orchestrator
# Handles mode activation, voice I/O in American accent, LLM calls, workflow routing

import asyncio
import os
import json
import re
import tempfile
import random
from core import config

try:
    import edge_tts
    import pygame
    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False

try:
    import sounddevice as sd
    import soundfile as sf
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False

from groq import Groq


# On-the-fly correction prompt
CORRECTION_SYSTEM = """You are an American English expert. The user wants help with their sentence.
Respond naturally in JSON:
{
  "corrected": "the corrected/improved version",
  "explanation": "brief explanation of what was changed and why"
}
"""

ONTHEFLY_INTENTS = {
    "correct my sentence": "correct",
    "make it more professional": "professional",
    "make it professional": "professional",
    "make it shorter": "shorter",
    "give me 3 alternative ways": "alternatives",
    "explain this in simple english": "explain",
    "explain in simple english": "explain",
}


class CoachInterrupt(Exception):
    def __init__(self, intent, details):
        self.intent = intent
        self.details = details
        super().__init__(f"Interrupt: {intent} - {details}")


class CoachEngine:
    """Main English Coach orchestrator. Manages mode, voice I/O, and workflow routing."""

    def __init__(self, brain, tts_engine=None):
        self.brain = brain
        self.tts_engine = tts_engine  # Fallback to main TTS if needed
        self.is_active = False
        self.current_mode = None
        self.speaking_duration = config.ENGLISH_COACH_SPEAKING_DURATION
        self.style_instruction = "Speak normally."
        self.transcript_callback = None  # To be set by UI
        self.get_rate_callback = None     # To be set by UI
        self.on_speak_callback = None     # To be set by UI: (bool) -> None
        self.on_listen_callback = None    # To be set by UI: (bool) -> None
        self.on_transcription_callback = None # To be set by UI: (str) -> None
        self._last_spoken_text = ""      # For explain-again feature
        self._stop_listen_event = None   # Initialized in start() or on demand

        # STT client (English-only mode)
        self.groq_client = Groq(api_key=config.GROK_API_KEY)

        # Workflow instances (lazy init)
        self._speaking = None
        self._pronunciation = None
        self._presentation = None
        self._interview = None
        self._practice = None

        # Load last session state for resume
        self._load_session_state()

        pass # print("[OK] English Coach Engine initialized", flush=True)

    def _load_session_state(self):
        try:
            from .progress_tracker import progress_tracker
            state = progress_tracker.load_session_state()
            self._last_session_mode = state.get("mode")
            self._last_session_sub_state = state.get("sub_state")
        except Exception:
            self._last_session_mode = None
            self._last_session_sub_state = None

    # ════════════════════════════════════════════
    # VOICE I/O (American Accent)
    # ════════════════════════════════════════════
    async def speak(self, text, update_transcript=True):
        """Speak text in American accent using Edge TTS."""
        if not text or not text.strip():
            return
        self._last_spoken_text = text  # Track for explain-again

        # Push to transcript UI
        if update_transcript and self.transcript_callback:
            self.transcript_callback(text)

        if self.on_speak_callback:
            self.on_speak_callback(True)

        if EDGE_AVAILABLE:
            tmp = None
            try:
                voice = config.ENGLISH_COACH_VOICE  # en-US-JennyNeural
                rate = self.get_rate_callback() if self.get_rate_callback else "+0%"
                tmp = os.path.join(
                    os.environ.get('TEMP', 'C:\\temp'),
                    f"coach_{os.getpid()}_{int(asyncio.get_event_loop().time()*1000)}.mp3"
                )

                communicate = edge_tts.Communicate(text, voice, rate=rate, pitch="+0Hz")
                await asyncio.wait_for(communicate.save(tmp), timeout=15.0)

                if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
                    pass # print(f"[COACH] Empty audio - skipping", flush=True)
                    return

                # Ensure pygame mixer is initialized
                if not pygame.mixer.get_init():
                    pygame.mixer.init()

                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()

                start_time = asyncio.get_event_loop().time()
                while pygame.mixer.music.get_busy():
                    if not self.is_active:
                        pygame.mixer.music.stop()
                        break
                    if asyncio.get_event_loop().time() - start_time > 30:
                        pygame.mixer.music.stop()
                        break
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                raise
            except Exception as e:
                # Fallback to main TTS
                if self.tts_engine:
                    await self.tts_engine.speak(text)
            finally:
                if pygame.mixer.get_init():
                    try:
                        pygame.mixer.music.unload()
                    except Exception: pass
                try:
                    if tmp and os.path.exists(tmp): os.remove(tmp)
                except Exception: pass
        elif self.tts_engine:
            await self.tts_engine.speak(text)
        
        if self.on_speak_callback:
            self.on_speak_callback(False)

    async def listen(self, duration=15, skip_intent=False):
        """Record and transcribe. Continuously streams audio for real-time UI updates."""
        if not SD_AVAILABLE:
            return ""

        import queue
        import numpy as np

        q = queue.Queue()

        def callback(indata, frames, time, status):
            q.put(indata.copy())

        sample_rate = 16000
        
        if self.on_listen_callback:
            self.on_listen_callback(True)

        audio_frames = []
        final_text = ""
        loop = asyncio.get_event_loop()
        
        start_time = loop.time()
        last_transcribe_time = start_time
        transcribe_interval = 1.0  # Fast UI updates every 1 second
        
        transcribing = False

        if self._stop_listen_event:
            self._stop_listen_event.clear()

        try:
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', callback=callback):
                while self.is_active:
                    if self._stop_listen_event and self._stop_listen_event.is_set():
                        break

                    current_time = loop.time()
                    elapsed = current_time - start_time
                    
                    if elapsed >= duration:
                        break
                        
                    while not q.empty():
                        audio_frames.append(q.get())
                        
                    if current_time - last_transcribe_time >= transcribe_interval and not transcribing and len(audio_frames) > 0:
                        last_transcribe_time = current_time
                        
                        current_data = np.concatenate(audio_frames, axis=0)
                        if len(current_data) > sample_rate * 0.5:
                            transcribing = True
                            
                            async def do_transcribe():
                                text = await self._transcribe_audio_data(current_data, sample_rate)
                                if text and self.on_transcription_callback:
                                    self.on_transcription_callback(text)
                                return text
                                
                            def on_done(task):
                                nonlocal transcribing
                                transcribing = False
                                
                            task = loop.create_task(do_transcribe())
                            task.add_done_callback(on_done)

                    await asyncio.sleep(0.1)
                    
            # Wait for last intermediate transcription to finish before final
            while transcribing:
                await asyncio.sleep(0.05)
                
            while not q.empty():
                audio_frames.append(q.get())
                
            if len(audio_frames) > 0:
                current_data = np.concatenate(audio_frames, axis=0)
                final_text = await self._transcribe_audio_data(current_data, sample_rate)
                if final_text and self.on_transcription_callback:
                    self.on_transcription_callback(final_text)
                
        except CoachInterrupt:
            raise
        except Exception as e:
            pass
        finally:
            if self.on_listen_callback:
                self.on_listen_callback(False)

        if final_text and not skip_intent:
            try:
                await self._handle_intents(final_text)
            except CoachInterrupt:
                raise
                
        return final_text

    async def _transcribe_audio_data(self, audio_data, sample_rate):
        """Helper to save numpy array to wav and transcribe with Groq via executor."""
        loop = asyncio.get_event_loop()
        tmp_filename = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_filename = tmp_file.name
                sf.write(tmp_filename, audio_data, sample_rate)
            
            def call_groq():
                with open(tmp_filename, "rb") as audio_file:
                    return self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3",
                        language="en",
                        response_format="text",
                        temperature=0.0,
                        prompt="Transcribe accurately."
                    )
                    
            transcription = await loop.run_in_executor(None, call_groq)
            text = str(transcription).strip() if not hasattr(transcription, 'text') else transcription.text.strip()
            
            # Filter noise
            hallucinations = ["thank you for watching", "subtitles by", "please subscribe", "thank you.", "thank you"]
            lower_text = text.lower()
            if any(h in lower_text for h in hallucinations) and len(text.split()) <= 3:
                return ""
            return text
        except Exception:
            return ""
        finally:
            if tmp_filename and os.path.exists(tmp_filename):
                try:
                    os.remove(tmp_filename)
                except:
                    pass

    async def _handle_intents(self, text):
        """Determine if we need to switch modes, style, or handle a meta-request."""
        intent_res = await self._analyze_intent(text)
        if intent_res:
            intent = intent_res.get("intent", "none")
            details = intent_res.get("details", "")
            if intent == "change_mode": raise CoachInterrupt("change_mode", details)
            elif intent == "stop_session": raise CoachInterrupt("stop_session", details)
            elif intent == "style_change":
                self.style_instruction = details
                await self.speak(f"Style updated: {details}")
            elif intent == "query_capabilities":
                await self.speak("I can help with speaking, pronunciation, interviews, or chat.")
            elif intent == "explain_again":
                if self._last_spoken_text:
                    await self.speak("Explaining again...")
                    res = await self.ask_llm(f"Simplify this for a student: {self._last_spoken_text}", "JSON: {explanation: ...}")
                    if res: await self.speak(res.get("explanation", ""))
            elif intent == "general_chat":
                await self.speak(details)
                await self.speak("Let's get back to it.")

    # ════════════════════════════════════════════
    # LLM CALLS (reuses Brain's provider chain)
    # ════════════════════════════════════════════
    async def ask_llm(self, user_message, system_prompt):
        """Send a message to LLM and get parsed JSON response."""
        
        if hasattr(self, 'style_instruction') and self.style_instruction and self.style_instruction != "Speak normally.":
            system_prompt = f"USER PREFERENCE: {self.style_instruction}\nYou must strictly follow the user preference above in your response.\n\n" + system_prompt
            
        loop = asyncio.get_event_loop()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # Use Brain's provider chain
        for i, model_cfg in enumerate(config.TEXT_MODELS_CHAIN):
            name = model_cfg["name"]
            provider = model_cfg["provider"]
            model = model_cfg["model"]

            client = self.brain.provider_clients.get(provider)
            if not client:
                client = self.brain._get_client(provider)
                if not client:
                    continue

            try:
                r = await loop.run_in_executor(
                    None,
                    lambda c=client, m=model, msgs=messages: c.chat.completions.create(
                        model=m,
                        messages=msgs,
                        temperature=0.3,
                        max_tokens=1500,
                    )
                )

                if not r or not hasattr(r, 'choices') or not r.choices:
                    continue

                content = r.choices[0].message.content
                result = self.brain._parse_json(content)
                if result and isinstance(result, dict):
                    return result

            except Exception as e:
                pass # print(f"[COACH] LLM {name} error: {str(e)[:80]}", flush=True)
                continue

        pass # print("[COACH] All LLM models failed", flush=True)
        return None

    # ════════════════════════════════════════════
    # MODE MANAGEMENT
    # ════════════════════════════════════════════
    async def start(self, mode=None, entities=None):
        """Start English Coach in specified mode, or prompt for one."""
        self.is_active = True
        self._stop_listen_event = asyncio.Event()
        
        if not mode:
            # Check if there's a saved last session to resume
            last_mode = self._last_session_mode
            
            if last_mode and last_mode not in ("daily", None):
                await self.speak(
                    f"Welcome back! Last time you were in {last_mode} mode. "
                    f"Would you like to continue with {last_mode}, or try something else?"
                )
                user_choice = await self.listen(duration=10, skip_intent=True)
            else:
                await self.speak(
                    "Hello! I'm your English coach. What would you like to practice today? "
                    "You can say: Speaking, Pronunciation, Interview, or just Chat."
                )
                user_choice = await self.listen(duration=10, skip_intent=True)
            
            if not user_choice:
                # Ask once more, then wait — DO NOT auto-start daily routine
                await self.speak("I'm here! Just say: Speaking, Pronunciation, Interview, or Chat.")
                user_choice = await self.listen(duration=12, skip_intent=True)

            if user_choice:
                system = """Analyze the user's response and extract the desired mode. Return JSON:
{
  "mode": "speaking|pronunciation|presentation|interview|daily|chat|stop|resume",
  "topic": "extracted topic or null",
  "style": "extracted style preference or 'Speak normally.'"
}"""
                res = await self.ask_llm(user_choice, system)
                if res and "mode" in res:
                    mode = res.get("mode", "chat")
                    if mode == "stop":
                        await self.stop()
                        return
                    if mode == "resume" and last_mode:
                        mode = last_mode
                    topic = res.get("topic")
                    self.style_instruction = res.get("style", "Speak normally.")
                    if topic:
                        if entities is None:
                            entities = {}
                        entities["text"] = topic
                else:
                    # Still no mode detected — go to chat as friendly fallback, NOT daily
                    mode = "chat"
            else:
                # No speech at all — exit gracefully, don't start daily
                await self.speak("No problem! Click any practice button whenever you're ready.")
                return

        self.current_mode = mode
        try:
            from .progress_tracker import progress_tracker
            progress_tracker.save_session_state(self.current_mode)
        except Exception:
            pass

        try:
            if mode == "daily":
                await self._run_daily_routine()
            elif mode == "speaking":
                # 🔧 FIX: Prompt for topic in speaking mode
                if entities and entities.get("text"):
                    topic = entities.get("text")
                else:
                    await self.speak("What topic would you like to speak about? Or say 'any' for a random one.")
                    user_topic = await self.listen(duration=10, skip_intent=True)
                    if user_topic and "any" not in user_topic.lower():
                        # Extract clean topic
                        system = "Extract the core topic from the user's sentence. Return ONLY the topic name (1-3 words). Example: 'I want to talk about AI' -> 'Artificial Intelligence'"
                        res = await self.ask_llm(user_topic, system)
                        topic = res.get("topic") if (res and isinstance(res, dict)) else user_topic
                    else:
                        topic = "Random Topic"
                
                await self._get_speaking().run(topic=topic)
            elif mode == "pronunciation":
                await self._get_pronunciation().run()
            elif mode == "presentation":
                await self._get_presentation().run()
            elif mode == "interview":
                await self._get_interview().run()
            elif mode == "practice":
                await self._get_practice().run()
            elif mode == "chat":
                await self._run_casual_chat()

            else:
                await self.speak(f"Unknown mode: {mode}.")
        except asyncio.CancelledError:
            self.is_active = False
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
            raise
        except CoachInterrupt as ci:
            if ci.intent == "change_mode":
                await self.speak(f"Switching to {ci.details} mode immediately.")
                await self.start(mode=ci.details, entities=entities)
            elif ci.intent == "stop_session":
                await self.stop()
        except Exception as e:
            await self.speak(f"Oops! Something went wrong: {e}")
        finally:
            self.is_active = False
            self.current_mode = None

    async def stop(self):
        """Stop English Coach mode."""
        self.is_active = False
        self.current_mode = None
        await self.speak("English Coach stopped. See you next time!")

    async def speak_explain(self, text):
        """Speak an explanation (same as speak, used by listen test)."""
        await self.speak(text)

    def stop_listen(self):
        """Signal to stop the current listen() loop."""
        if self._stop_listen_event:
            self._stop_listen_event.set()

    async def _run_casual_chat(self):
        """
        Chat mode with two sub-modes:
        1. Casual Chat: Friendly, natural, short replies.
        2. Discussion: Randomly selected topic, facilitated by AI.
        """
        await self.speak("Would you like a casual chat, or would you like to discuss a specific topic today?")
        choice_text = await self.listen(duration=10, skip_intent=True)
        
        mode = "casual"
        discussion_topic = None
        
        if choice_text:
            res = await self.ask_llm(
                choice_text, 
                "Identify if the user wants 'casual chat' or 'topic discussion'. Return JSON: {'choice': 'casual|discussion', 'topic': 'extracted topic if any'}"
            )
            if res:
                mode = res.get("choice", "casual")
                discussion_topic = res.get("topic")

        if mode == "discussion":
            if not discussion_topic:
                topics = ["Global warming", "Artificial Intelligence", "Healthy Lifestyle", "Travel & Tourism", "Space Exploration", "Traditional Food", "Future of Work"]
                discussion_topic = random.choice(topics)
            
            await self.speak(f"Great! Let's discuss {discussion_topic}. What are your thoughts on this?")
            CHAT_SYSTEM = f"""You are a skilled English discussion facilitator. The topic is: {discussion_topic}.
RULES:
- Keep your replies VERY SHORT (1 sentence). 
- Your goal is to make the USER speak more. Ask ONE pointed question to keep them talking.
- AI should occupy only 20% of the conversation. Focus on the user's opinions.
- Gently correct any major English mistakes in your short response.
Return JSON: {{"reply": "your short conversational reply and question"}}"""
        else:
            await self.speak("Sure thing! Let's just chat casually.")
            CHAT_SYSTEM = """You are a friendly English conversation partner. Chat casually and naturally.
RULES:
- Keep replies SHORT: 1-2 sentences maximum.
- STAY on the same topic the user is talking about.
- DO NOT start new topics randomly.
- Be brief and conversational.
- Gently note any major English mistakes.
Return JSON: {"reply": "your short conversational reply"}"""

        chat_history = []
        max_history = 6

        while self.is_active:
            user_text = await self.listen(duration=15)
            if not user_text: continue

            stop_words = ["stop", "bye", "goodbye", "exit", "end chat", "quit", "band karo", "bas karo"]
            if any(w in user_text.lower() for w in stop_words):
                await self.speak("Okay, talk to you later!")
                break

            chat_history.append({"role": "user", "content": user_text})
            if len(chat_history) > max_history * 2: chat_history = chat_history[-max_history * 2:]

            history_context = ""
            if len(chat_history) > 1:
                history_context = "Previous conversation:\n" + "\n".join(
                    f"{m['role'].title()}: {m['content']}" for m in chat_history[:-1]
                ) + "\n\n"

            prompt = f"{history_context}User just said: \"{user_text}\""
            res = await self.ask_llm(prompt, CHAT_SYSTEM)

            if res and "reply" in res:
                reply = res["reply"]
                await self.speak(reply, update_transcript=True)
                chat_history.append({"role": "assistant", "content": reply})

    # ════════════════════════════════════════════
    # DAILY ROUTINE 
    # ════════════════════════════════════════════
    async def _run_daily_routine(self):
        """Full daily routine: warm-up → speaking → pronunciation → interview."""
        await self.speak("Starting your daily English practice. Let's go!")
        await asyncio.sleep(0.5)

        # 1. Warm-up shadowing (2 min)
        if self.is_active:
            await self.speak("Step 1: Warm-up shadowing. I'll say 3 sentences, you repeat after each one.")
            warmup_sentences = [
                "I'm a computer science student focused on web development.",
                "My latest project uses React for the frontend and Node.js for the backend.",
                "I enjoy solving complex problems and building practical applications."
            ]
            for sentence in warmup_sentences:
                if not self.is_active:
                    break
                await self.speak(sentence)
                await asyncio.sleep(0.5)
                await self.speak("Your turn.")
                user_repeat = await self.listen(duration=10)
                if user_repeat:
                    await self.speak("Good!")
                await asyncio.sleep(0.3)

        # 2. Speaking practice (8 min)
        if self.is_active:
            await self.speak("Step 2: Speaking prompts.")
            await self._get_speaking().run()

        # 3. Pronunciation (5 min)
        if self.is_active:
            await self.speak("Step 3: Pronunciation drill.")
            await self._get_pronunciation().run()

        # 4. Interview Q&A (5 min)
        if self.is_active:
            await self.speak("Step 4: Quick interview question.")
            await self._get_interview().run()

        if self.is_active:
            # Weekly summary
            from .progress_tracker import progress_tracker
            summary = progress_tracker.get_weekly_summary()
            await self.speak(f"Daily practice complete! {summary}")

    # ════════════════════════════════════════════
    # ON-THE-FLY CORRECTION
    # ════════════════════════════════════════════
    async def handle_correction(self, command):
        """Handle on-the-fly correction commands."""
        # Determine what type of correction
        cmd_lower = command.lower()
        
        for trigger, action in ONTHEFLY_INTENTS.items():
            if trigger in cmd_lower:
                # Extract the user's text (everything after the trigger)
                user_text = cmd_lower.split(trigger, 1)[-1].strip().strip(":").strip()
                if not user_text:
                    await self.speak("Please say your sentence after the command.")
                    return

                if action == "correct":
                    system = "Correct this English sentence. Return JSON: {\"corrected\": \"...\", \"explanation\": \"...\"}"
                elif action == "professional":
                    system = "Make this sentence more professional. Return JSON: {\"corrected\": \"...\", \"explanation\": \"...\"}"
                elif action == "shorter":
                    system = "Make this shorter (max 30 seconds spoken). Return JSON: {\"corrected\": \"...\", \"explanation\": \"...\"}"
                elif action == "alternatives":
                    system = "Give 3 alternative ways to say this. Return JSON: {\"alternatives\": [\"...\", \"...\", \"...\"]}"
                elif action == "explain":
                    system = "Explain this in very simple English. Return JSON: {\"explanation\": \"...\"}"
                else:
                    system = CORRECTION_SYSTEM

                result = await self.ask_llm(user_text, system)
                if result:
                    if "corrected" in result:
                        await self.speak(f"Better version: {result['corrected']}")
                        try:
                            from .progress_tracker import progress_tracker
                            progress_tracker.log_mistake(user_text, result['corrected'], context="On-the-fly Correction")
                        except Exception:
                            pass
                        if result.get("explanation"):
                            await self.speak(result["explanation"])
                    elif "alternatives" in result:
                        for i, alt in enumerate(result["alternatives"][:3]):
                            await self.speak(f"Option {i+1}: {alt}")
                    elif "explanation" in result:
                        await self.speak(result["explanation"])
                else:
                    await self.speak("Sorry, couldn't process that. Try again.")
                return True

        return False

    # ════════════════════════════════════════════
    # LAZY WORKFLOW INIT
    # ════════════════════════════════════════════
    def _get_speaking(self):
        if not self._speaking:
            from .speaking_practice import SpeakingPractice
            self._speaking = SpeakingPractice(self)
        return self._speaking

    def _get_pronunciation(self):
        if not self._pronunciation:
            from .pronunciation_drill import PronunciationDrill
            self._pronunciation = PronunciationDrill(self)
        return self._pronunciation

    def _get_presentation(self):
        if not self._presentation:
            from .presentation_rehearsal import PresentationRehearsal
            self._presentation = PresentationRehearsal(self)
        return self._presentation

    def _get_interview(self):
        if not self._interview:
            from .mock_interview import MockInterview
            self._interview = MockInterview(self)
        return self._interview

    def _get_practice(self):
        if not self._practice:
            from .practice_lab import PracticeLab
            self._practice = PracticeLab(self)
        return self._practice

    async def _analyze_intent(self, text):
        system = f"""Analyze the user's transcript to determine if they want a meta-action.
Current Practice Mode: {self.current_mode}

Intent categories:
- style_change: User asks to change how you speak (e.g., 'short sentences', 'speak slower').
- change_mode: User wants to change mode ('speaking', 'pronunciation', 'presentation', 'interview', 'daily', 'chat').
- query_capabilities: User asks what you can do.
- report_progress: User asks about their progress, improvement, or mistakes.
- explain_again: User didn't understand something and wants it explained again. Look for: 'samjha do', 'mera word samjha do', 'explain again', 'dobara batao', 'i don't understand', 'what did you mean', 'can you repeat that', 'huh', 'didn't get it', 'explain that', 'what does that mean'.
- stop_session: User wants to stop, exit, or end the practice session completely.
- general_chat: User asks a random question or makes a chatty remark completely unrelated to the current practice. IMPORTANT: If Current Practice Mode is 'chat', treat all normal conversation as 'none', NOT 'general_chat'.
- none: Normal continuation of practice or answer to a prompt.

If general_chat, the 'details' field MUST contain your friendly answer to their question.
If change_mode or style_change, the 'details' field contains the extracted target.
Return JSON:
{{
  "intent": "style_change|change_mode|query_capabilities|report_progress|explain_again|stop_session|general_chat|none",
  "details": "string"
}}"""
        return await self.ask_llm(text, system)

    async def _speak_progress_diagnostic(self):
        try:
            from .progress_tracker import progress_tracker
            weak = progress_tracker.data.get("weak_words", [])
            grammar = progress_tracker.data.get("grammar_mistakes", [])
            system = """You are an English coach diagnostic engine.
Data: Weak Words={weak}, Grammar Mistakes={grammar}.
Give a concise diagnostic report (max 3 sentences) highlighting exactly where they are making mistakes and specific advice on how to improve. If data is empty, just encourage them to practice more so you can generate a report.
Return JSON: {"report": "the spoken report"}"""
            
            prompt = system.replace("{weak}", str(weak)).replace("{grammar}", str(grammar))
            res = await self.ask_llm("Analyze progress", prompt)
            if res and "report" in res:
                await self.speak(res["report"])
            else:
                await self.speak("Keep practicing directly with me to gather more data for your report.")
        except Exception as e:
            pass # print(f"[COACH] Diagnostic error: {e}")
            await self.speak("I'm unable to load your diagnostic progress right now.")
