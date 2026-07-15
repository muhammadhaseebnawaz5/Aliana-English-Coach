# english_coach/speaking_practice.py - Free Speaking Practice Module

import asyncio
import re
import time
from .progress_tracker import progress_tracker

class SpeakingPractice:
    def __init__(self, coach):
        self.coach = coach
        self.is_running = False
        self.full_transcript = ""
        self.filler_words = ["um", "uh", "err", "ah", "like", "basically", "you know", "actually", "sort of", "kind of"]

    async def run(self, topic=None):
        """Starts a speaking practice session with a professional paragraph and session looping."""
        while True:
            self.is_running = True
            self.full_transcript = ""
            
            # 1. Mode Selection (only ask if topic is not provided or it's a new session)
            if not topic:
                await self.coach.speak("Would you like to speak freely, or should I give you a professional script to read first?")
                mode_res = await self.coach.listen(duration=8, skip_intent=True)
                is_guided = "script" in (mode_res or "").lower() or "read" in (mode_res or "").lower() or "guided" in (mode_res or "").lower()
            else:
                # If topic was passed from engine, assume guided unless specified
                is_guided = True

            # 2. Topic Selection
            if not topic:
                await self.coach.speak("What topic would you like to practice today?")
                topic_input = await self.coach.listen(duration=10, skip_intent=True)
                if topic_input and "any" not in topic_input.lower():
                    # Extract clean topic
                    system = "Extract the core topic. Return ONLY the topic name (1-3 words). Example: 'I want to talk about AI' -> 'Artificial Intelligence'"
                    res = await self.coach.ask_llm(topic_input, system)
                    topic = res.get("topic") if (res and isinstance(res, dict)) else topic_input
                else:
                    topic = "Modern Technology"

            duration_sec = 60 # Default duration for script reading

            if is_guided:
                # Generate a professional comprehensive paragraph
                await self.coach.speak(f"Generating a sophisticated professional script about {topic} for you.")
                system_prompt = f"""Generate a comprehensive professional practice paragraph (70-100 words) about '{topic}'.
    RULES:
    - Use sophisticated vocabulary and complex sentence structures.
    - Include tricky words, advanced terminology, and professional phrasing.
    - The content must be informative and formal.
    - NO questions. Just one solid paragraph.
    Return ONLY JSON: {{'script': 'The full paragraph here...'}}"""
                res = await self.coach.ask_llm("Generate advanced script", system_prompt)
                
                if res and isinstance(res, dict):
                    script_text = res.get("script", f"{topic} is becoming increasingly significant in modern application development because it allows developers to create more intelligent, efficient, and personalized digital experiences. Nowadays, many sophisticated applications integrate specialized features such as virtual assistants and predictive analytics to enhance user interaction. This technological advancement is revolutionizing the industry and encouraging innovation across multiple sectors, including healthcare and finance.")
                else:
                    script_text = f"{topic} represents a paradigm shift in contemporary professional environments, demanding a higher level of technical proficiency and adaptability from practitioners. The integration of such methodologies facilitates enhanced operational efficiency while concurrently fostering a culture of continuous improvement. Furthermore, the capacity to leverage these advancements effectively is often the differentiating factor between conventional performance and industry-leading innovation."
                
                display_text = (
                    f"📝 **Professional Guided Practice: {topic}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{script_text}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎤 Listen carefully, then repeat..."
                )
                if self.coach.transcript_callback:
                    self.coach.transcript_callback(display_text)
                
                await self.coach.speak("I will read this professional paragraph first. Pay attention to the flow and pronunciation.")
                await self.coach.speak(script_text, update_transcript=False)
                await asyncio.sleep(0.5)
                await self.coach.speak("Now, it is your turn. Please read the entire paragraph out loud with confidence.")
            else:
                # Free Speaking
                intro_text = (
                    f"🎤 **Free Speaking Mode**\n"
                    f"Topic: **{topic}**\n\n"
                    f"Goal: Speak freely for **{duration_sec // 60} minutes**."
                )
                if self.coach.transcript_callback:
                    self.coach.transcript_callback(intro_text)
                await self.coach.speak(f"Excellent. Please speak freely and professionally about {topic}. I am listening.")

            # 3. Setup Live UI Updates
            original_callback = self.coach.on_transcription_callback
            def live_subtitle(text):
                if self.coach.transcript_callback:
                    rem = getattr(self, 'remaining_time', duration_sec)
                    if rem is None: rem = 0
                    m, s = divmod(int(rem), 60)
                    timer_str = f"⏱️ {m:02d}:{s:02d}"
                    header = f"📝 Script Practice" if is_guided else f"🎤 Free Speaking"
                    self.coach.transcript_callback(f"{timer_str} | {header}\n\n🎤 **Live:**\n{text}")
                if original_callback:
                    original_callback(text)

            self.coach.on_transcription_callback = live_subtitle
            self.is_running = True

            # 4. Timer Task
            timer_task = asyncio.create_task(self._run_timer(duration_sec))
            
            try:
                # 5. Recording Session
                self.full_transcript = await self.coach.listen(duration=duration_sec, skip_intent=True)
            finally:
                self.is_running = False
                timer_task.cancel()
                self.coach.on_transcription_callback = original_callback

            # 6. Detailed Analysis
            await self.coach.speak("Analysis complete. Here is your performance report.")
            
            analysis = await self._analyze_speech(self.full_transcript, topic, duration_sec)
            
            # 7. Report & Save
            await self._display_report(analysis)
            
            if isinstance(analysis, dict) and "error" not in analysis:
                scores = analysis.get("scores", {})
                final_score = scores.get("overall", 0) if isinstance(scores, dict) else 0
                
                progress_tracker.log_session(
                    "speaking",
                    duration_min=duration_sec/60,
                    words_practiced=len(self.full_transcript.split()),
                    score=final_score,
                    details=analysis
                )
                # Track weak words
                for word in analysis.get("mispronounced_words", []):
                    progress_tracker.add_weak_word(word)

            # 8. Loop Prompt
            await self.coach.speak("Would you like to practice another topic, try this one again, or return to the main menu?")
            loop_res = await self.coach.listen(duration=8, skip_intent=True)
            if not loop_res: break
            
            lr = loop_res.lower()
            if "another" in lr or "new" in lr:
                topic = None
                continue
            elif "again" in lr or "repeat" in lr:
                continue
            else:
                break

    async def _run_timer(self, total_sec):
        self.remaining_time = total_sec
        while self.remaining_time > 0 and self.is_running:
            await asyncio.sleep(1)
            self.remaining_time -= 1

    async def _analyze_speech(self, transcript, topic, duration_sec):
        """Analyzes speech using LLM for qualitative and metrics for quantitative data."""
        if not transcript or len(transcript.strip()) < 10:
            return {"error": "Speech was too short for a meaningful analysis."}

        # 1. Metrics
        words = transcript.split()
        word_count = len(words)
        wpm = round((word_count / (duration_sec or 60)) * 60)
        
        fillers_detected = []
        for f in self.filler_words:
            count = len(re.findall(rf"\b{f}\b", transcript, re.IGNORECASE))
            if count > 0:
                fillers_detected.append({"word": f, "count": count})
        total_fillers = sum(f["count"] for f in fillers_detected)

        # 2. LLM Analysis
        system_prompt = f"""You are an Advanced AI Speaking Coach.
Analyze this speaking session on the topic: "{topic}".
Transcript: "{transcript}"

CRITICAL:
- Be encouraging but professional.
- Do NOT give 0 scores unless the transcript is completely unrelated or empty.
- Rate: Pronunciation, Fluency, Confidence, Professionalism (0-100).
- Identify informal phrases and provide professional alternatives.
- Provide ONE specific improved version of a key sentence the user said.

Return JSON:
{{
  "scores": {{
    "overall": 0-100,
    "pronunciation": 0-100,
    "fluency": 0-100,
    "confidence": 0-100,
    "professionalism": 0-100
  }},
  "topic_relevance": "Brief feedback on how well they stayed on topic.",
  "mispronounced_words": ["list"],
  "repeated_words": ["list"],
  "filler_analysis": "feedback on filler word usage",
  "professional_suggestions": [
    {{"informal": "phrase", "professional": "better phrase", "context": "why"}}
  ],
  "improved_example": {{
    "user_said": "a sentence from transcript",
    "polished": "highly professional version"
  }},
  "general_advice": "A short encouraging closing sentence."
}}"""

        llm_res = await self.coach.ask_llm("Analyze free speaking", system_prompt)
        
        # Robust fallback for None or non-dict response
        if not llm_res or not isinstance(llm_res, dict):
            return {"error": "Could not complete analysis."}

        # Combine
        llm_res.update({
            "topic": topic,
            "duration": f"{duration_sec//60}:{duration_sec%60:02d}",
            "word_count": word_count,
            "wpm": wpm,
            "total_fillers": total_fillers,
            "fillers_list": fillers_detected
        })
        
        return llm_res

    async def _display_report(self, analysis):
        if not analysis or "error" in analysis:
            await self.coach.speak(analysis.get("error", "Speech analysis failed.") if isinstance(analysis, dict) else "Speech analysis failed.")
            return

        scores = analysis.get("scores", {})
        if not isinstance(scores, dict): scores = {}
        
        report_md = (
            f"🎙️ **Speaking Performance Analysis**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Topic Focus:** {analysis.get('topic', 'General Conversation')}\n\n"
            f"📈 **Core Metrics:**\n"
            f"• **Fluency:** {scores.get('fluency', 0)}% (Speed: {analysis.get('wpm', 0)} WPM)\n"
            f"• **Pronunciation:** {scores.get('pronunciation', 0)}%\n"
            f"• **Professionalism:** {scores.get('professionalism', 0)}%\n\n"
            f"📝 **Vocabulary Insight:**\n"
            f"- **Filler Words:** {analysis.get('total_fillers', 0)} detected ({analysis.get('filler_analysis', 'N/A')})\n"
            f"- **Tricky Words:** {', '.join(analysis.get('mispronounced_words', ['None']))}\n\n"
            f"✨ **Professional Polish:**\n"
        )
        
        for sug in analysis.get("professional_suggestions", [])[:2]:
            if isinstance(sug, dict) and "informal" in sug and "professional" in sug:
                report_md += f"- Instead of *'{sug['informal']}'*, use **'{sug['professional']}'**.\n"

        improved = analysis.get("improved_example")
        if improved and isinstance(improved, dict):
            report_md += (
                f"\n💡 **Sentence Transformation:**\n"
                f"**Original:** \"{improved.get('user_said', '')}\"\n"
                f"**Polished:** \"{improved.get('polished', '')}\"\n"
            )

        report_md += f"\n🎯 **Coach's Advice:** {analysis.get('general_advice', 'Excellent work! Keep talking to build confidence.')}"

        if self.coach.transcript_callback:
            self.coach.transcript_callback(report_md)

        # Spoken Feedback
        await self.coach.speak(f"Speaking session complete! Your overall fluency score is {scores.get('overall', 0)} percent. {analysis.get('general_advice', 'Keep practicing!')}")
