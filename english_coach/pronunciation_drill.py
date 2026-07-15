# english_coach/pronunciation_drill.py - AI-Powered Pronunciation Trainer

import asyncio
import random
from core import config

class PronunciationDrill:
    def __init__(self, coach):
        self.coach = coach
        self.difficulty_levels = ["Easy", "Medium", "Hard"]
        
        self.word_bank = {
            "Easy": [
                {"word": "Honest", "meaning": "Truthful and sincere", "urdu_meaning": "دیانتدار", "syllables": "on · uhst", "phonetic": "ON-uhst"},
                {"word": "Island", "meaning": "A piece of land surrounded by water", "urdu_meaning": "جزیرہ", "syllables": "ai · luhnd", "phonetic": "EYE-luhnd"},
                {"word": "Debt", "meaning": "Money that is owed to someone", "urdu_meaning": "قرض", "syllables": "det", "phonetic": "DET"},
                {"word": "Queue", "meaning": "A line of people waiting", "urdu_meaning": "قطار", "syllables": "kyoo", "phonetic": "KYOO"},
                {"word": "Chaos", "meaning": "Complete disorder and confusion", "urdu_meaning": "افراتفری", "syllables": "kay · os", "phonetic": "KAY-oss"},
                {"word": "Salmon", "meaning": "A type of large fish", "urdu_meaning": "سائمن مچھلی", "syllables": "sam · uhn", "phonetic": "SAM-uhn"}
            ],
            "Medium": [
                {"word": "Comfortable", "meaning": "Providing physical ease and relaxation", "urdu_meaning": "آرام دہ", "syllables": "kuhmf · tuh · buhl", "phonetic": "KUMF-tuh-buhl"},
                {"word": "Vegetable", "meaning": "A plant used as food", "urdu_meaning": "سبزی", "syllables": "vej · tuh · buhl", "phonetic": "VEJ-tuh-buhl"},
                {"word": "Architecture", "meaning": "The art of designing buildings", "urdu_meaning": "فن تعمیر", "syllables": "aar · kuh · tek · cher", "phonetic": "AAR-kuh-tek-cher"},
                {"word": "Schedule", "meaning": "A plan for carrying out a process", "urdu_meaning": "شیڈول / نظام الاوقات", "syllables": "skej · ool", "phonetic": "SKEJ-ool"},
                {"word": "Library", "meaning": "A building containing collections of books", "urdu_meaning": "لائبریری", "syllables": "lai · bre · re", "phonetic": "LY-brer-ee"},
                {"word": "February", "meaning": "The second month of the year", "urdu_meaning": "فروری", "syllables": "feb · roo · er · ee", "phonetic": "FEB-roo-er-ee"}
            ],
            "Hard": [
                {"word": "Mischievous", "meaning": "Playfully causing trouble", "urdu_meaning": "شرارتی", "syllables": "mis · chuh · vuhs", "phonetic": "MIS-chuh-vuhs"},
                {"word": "Entrepreneur", "meaning": "A person who sets up a business", "urdu_meaning": "تاجر / کاروباری شخص", "syllables": "ahn · truh · pruh · nur", "phonetic": "AHN-truh-pruh-NUR"},
                {"word": "Phenomenon", "meaning": "A remarkable person or thing", "urdu_meaning": "مظہر / غیر معمولی واقعہ", "syllables": "fuh · nom · uh · non", "phonetic": "fuh-NOM-uh-non"},
                {"word": "Anemone", "meaning": "A type of sea creature or flower", "urdu_meaning": "شقائق النعمان", "syllables": "uh · nem · uh · nee", "phonetic": "uh-NEM-uh-nee"},
                {"word": "Otorhinolaryngologist", "meaning": "Ear, nose, and throat doctor", "urdu_meaning": "کان، ناک اور گلے کا ماہر", "syllables": "oh · toh · rai · noh · la · ring · gol · uh · jist", "phonetic": "OH-toh-RY-noh-LA-ring-GOL-uh-jist"},
                {"word": "Worcestershire", "meaning": "A type of savory sauce", "syllables": "wu · stuh · sher", "phonetic": "WUSS-tuh-sher"}
            ]
        }

    async def run(self):
        # Initial instruction
        intro_text = "🎯 AI Pronunciation Trainer\n\nI will help you master tricky English words through structured drills.\n\nReady to improve your accent?"
        if self.coach.transcript_callback:
            self.coach.transcript_callback(intro_text)
            
        await self.coach.speak("Welcome to your pronunciation drill. I'm preparing some fresh, tricky words for us to practice.")
        
        # Dynamically generate words via LLM to avoid hardcoding
        practice_words = await self._generate_practice_words()
        
        if not practice_words:
            # Fallback to a small random selection if LLM fails
            await self.coach.speak("I'll pick some classic tricky words for today.")
            practice_words = []
            all_words = self.word_bank["Easy"] + self.word_bank["Medium"] + self.word_bank["Hard"]
            practice_words = random.sample(all_words, 5)

        correct_count = 0
        from .progress_tracker import progress_tracker
        
        for i, word_data in enumerate(practice_words):
            if not self.coach.is_active:
                break
            
            word = word_data["word"]
            level = word_data.get("level", "Medium")
            
            # Show word info in transcript
            display = (
                f"🎯 Word {i+1} of {len(practice_words)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Word: **{word}**\n"
                f"Level: {level}\n"
                f"Meaning: {word_data['meaning']} ({word_data.get('urdu_meaning', '')})\n\n"
                f"Pronunciation: {word_data['syllables']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎤 Listen and then repeat..."
            )
            if self.coach.transcript_callback:
                self.coach.transcript_callback(display)

            # Speak word clearly
            await self.coach.speak(f"Word: {word}. Level: {level}. Meaning: {word_data['meaning']}.", update_transcript=False)
            await asyncio.sleep(0.3)
            await self.coach.speak(f"Listen closely: {word}.", update_transcript=False)
            await self.coach.speak(f"Now, you try. Say {word}.", update_transcript=False)
            
            # Listen to user
            user_speech = await self.coach.listen(duration=8)
            
            if not user_speech:
                await self.coach.speak("I didn't hear you. Let's try that one again later.", update_transcript=False)
                continue

            # Analyze pronunciation
            analysis = await self._analyze_pronunciation(word, user_speech, word_data)
            
            if analysis["is_correct"]:
                await self.coach.speak(f"Excellent! {analysis['feedback']}", update_transcript=False)
                correct_count += 1
                progress_tracker.mark_word_improved(word)
            else:
                # Provide feedback and start correction flow
                await self.coach.speak(analysis["feedback"], update_transcript=False)
                await self._correction_flow(word_data, analysis)
                
                # Final check after correction
                await self.coach.speak(f"Now try the full word again: {word}.", update_transcript=False)
                retry = await self.coach.listen(duration=8)
                if retry and word.lower() in retry.lower():
                    await self.coach.speak("Much better! Great improvement.", update_transcript=False)
                    correct_count += 1
                else:
                    await self.coach.speak(f"That's a tough one. We'll keep practicing {word} in future sessions.", update_transcript=False)
                    progress_tracker.add_weak_word(word)
            
            await asyncio.sleep(1.0)
            
        summary = f"Drill complete. You mastered {correct_count} out of {len(practice_words)} tricky words today!"
        if self.coach.transcript_callback:
            self.coach.transcript_callback(f"📊 Drill Complete\n\nFinal Score: {correct_count}/{len(practice_words)}\n\n{summary}")
            
        await self.coach.speak(summary)

    async def _generate_practice_words(self):
        """Use LLM to generate a fresh set of practice words, avoiding repetition."""
        from .progress_tracker import progress_tracker
        weak_words = progress_tracker.data.get("weak_words", [])
        improved_words = progress_tracker.data.get("improved_words", [])
        
        system_prompt = f"""Generate 5 UNIQUE English words for pronunciation practice. 
USER PROGRESS:
- Weak words to practice again: {weak_words[:5]}
- Already improved words (DO NOT USE THESE): {improved_words}

IMPORTANT:
- Do NOT use very basic/common words like 'tree', 'water', 'book'.
- Select words useful for pronunciation (complex syllables, tricky sounds, stress patterns).
- Include: 1 Easy, 2 Medium, 2 Hard.
- Easy: Slightly tricky (e.g., 'honest', 'island').
- Medium: Multi-syllable or irregular (e.g., 'comfortable', 'vegetable').
- Hard: Complex or commonly mispronounced (e.g., 'mischievous', 'entrepreneur').

Return JSON format:
{{
  "words": [
    {{
      "word": "String",
      "level": "Easy|Medium|Hard",
      "meaning": "Simple English meaning",
      "urdu_meaning": "Urdu meaning",
      "syllables": "syllable · break · down",
      "phonetic": "SIMPLE-phonetic-style"
    }}
  ]
}}"""
        
        try:
            result = await self.coach.ask_llm("Generate 5 fresh practice words.", system_prompt)
            if result and "words" in result and isinstance(result["words"], list):
                return result["words"]
        except Exception:
            pass
        return None

    def _get_level_for_word(self, word):
        for level, words in self.word_bank.items():
            if any(w["word"] == word for w in words):
                return level
        return "Medium"

    async def _analyze_pronunciation(self, target_word, user_transcript, word_data):
        """Use LLM to compare transcript with target and detect specific errors."""
        
        system_prompt = f"""You are a professional English Pronunciation Coach.
Target Word: {target_word}
Syllables: {word_data['syllables']}
Phonetic: {word_data['phonetic']}

The user was asked to say this word. Their speech was transcribed as: "{user_transcript}"

Task:
1. Determine if the pronunciation was acceptable (True/False). 
   - Note: Whisper transcription might "fix" minor errors, so if the transcript matches exactly, it's likely correct.
   - If the transcript is different or contains phonetic misspellings, detect the error.
2. If incorrect, identify which part was wrong: "beginning", "middle", "ending", or "full".
3. Provide precise feedback like: "You pronounced 'mis' correctly, but 'chievous' is incorrect."
4. Provide correction steps (list of syllables/parts).

Return JSON:
{{
  "is_correct": bool,
  "detected_error_part": "beginning|middle|ending|full|none",
  "feedback": "string",
  "correction_steps": ["part1", "part2", ...]
}}"""

        result = await self.coach.ask_llm(f"User said: {user_transcript}", system_prompt)
        if not result:
            # Fallback if LLM fails
            is_correct = target_word.lower() in user_transcript.lower()
            return {
                "is_correct": is_correct,
                "detected_error_part": "none" if is_correct else "full",
                "feedback": "Perfect!" if is_correct else f"That didn't sound quite like {target_word}.",
                "correction_steps": word_data["syllables"].split(" · ")
            }
        return result

    async def _correction_flow(self, word_data, analysis):
        """Teach the word step by step."""
        word = word_data["word"]
        steps = analysis.get("correction_steps", word_data["syllables"].split(" · "))
        
        await self.coach.speak(f"Let's break down {word} into parts.")
        
        for step in steps:
            if not self.coach.is_active: break
            
            clean_step = step.strip()
            await self.coach.speak(f"Say: {clean_step}")
            user_part = await self.coach.listen(duration=5)
            
            # Briefly acknowledge
            if user_part:
                await self.coach.speak("Good.")
            await asyncio.sleep(0.3)

        await self.coach.speak(f"Now combine them: {'-'.join(steps)}")
        await asyncio.sleep(0.5)
