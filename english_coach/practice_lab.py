# english_coach/practice_lab.py - Daily Practice Engine

import asyncio
import random
import time
from .progress_tracker import progress_tracker

class PracticeLab:
    def __init__(self, coach):
        self.coach = coach
        self.session_data = {
            "drills_completed": 0,
            "correct": 0,
            "total_words": 0,
            "scores": []
        }

    async def run(self):
        """Starts a full daily practice session."""
        await self.coach.speak("Welcome to the Practice Lab. Let's start your daily speaking workout.")
        
        # 1. Warm-up (Word Repetition)
        await self._run_warmup()
        
        if not self.coach.is_active: return

        # 2. Core Practice (Syllable Breakdown & Speed Drill)
        await self._run_core_practice()

        if not self.coach.is_active: return

        # 3. Challenge Round (Sentence Fluency)
        await self._run_challenge()

        # 4. Wrap up & Log
        await self._finish_session()

    async def _run_warmup(self):
        """Warm-up: Repeat 3 words, including weak words from tracker."""
        await self.coach.speak("Step 1: Warm-up. Repeat these words clearly.")
        
        # Get weak words for personalization
        weak_words = progress_tracker.get_weak_words(2)
        
        system_prompt = f"""Generate 3 warm-up words for English practice.
Include these weak words if any: {weak_words}
Return JSON:
{{
  "exercises": [
    {{"word": "string", "meaning": "string", "syllables": "string", "level": "Easy"}}
  ]
}}"""
        res = await self.coach.ask_llm("Generate warm-up", system_prompt)
        if res and "exercises" in res:
            for ex in res["exercises"]:
                if not self.coach.is_active: break
                
                display = f"🔥 Warm-up\n\nWord: **{ex['word']}**\nMeaning: {ex['meaning']}\nSyllables: {ex['syllables']}"
                if self.coach.transcript_callback: self.coach.transcript_callback(display)
                
                await self.coach.speak(f"Please say: {ex['word']}")
                user_speech = await self.coach.listen(duration=5)
                
                if user_speech and ex['word'].lower() in user_speech.lower():
                    await self.coach.speak("Good!")
                    self.session_data["correct"] += 1
                else:
                    await self.coach.speak("Keep practicing that one.")
                
                self.session_data["drills_completed"] += 1
                self.session_data["total_words"] += 1

    async def _run_core_practice(self):
        """Core: Syllable breakdown and Speed Drill."""
        await self.coach.speak("Step 2: Core Practice. Syllable breakdown and Speed Drill.")
        
        # 1. Syllable Breakdown
        word_to_break = random.choice(["Entrepreneur", "Mischievous", "Phenomenon", "Otorhinolaryngologist", "Worcestershire"])
        syllables = {
            "Entrepreneur": ["ahn", "truh", "pruh", "nur"],
            "Mischievous": ["mis", "chuh", "vuhs"],
            "Phenomenon": ["fuh", "nom", "uh", "non"],
            "Worcestershire": ["wu", "stuh", "sher"]
        }.get(word_to_break, ["test"])
        
        if self.coach.transcript_callback:
            self.coach.transcript_callback(f"🧠 Syllable Breakdown\n\nWord: **{word_to_break}**\nSteps: {' · '.join(syllables)}")
            
        await self.coach.speak(f"Let's break down the word: {word_to_break}.")
        for s in syllables:
            if not self.coach.is_active: break
            await self.coach.speak(f"Say: {s}")
            await self.coach.listen(duration=4)
        
        await self.coach.speak(f"Now say the full word: {word_to_break}")
        await self.coach.listen(duration=6)

        # 2. Speed Drill
        await self.coach.speak("Speed Drill! Repeat these three words as fast and clearly as you can.")
        words = ["Blue", "Build", "Blast"]
        if self.coach.transcript_callback:
            self.coach.transcript_callback(f"⚡ Speed Drill\n\nWords: {' -> '.join(words)}\n\nGo fast!")
            
        await self.coach.speak(f"Repeat: {'... '.join(words)}")
        await self.coach.listen(duration=8)

    async def _run_challenge(self):
        """Challenge: Sentence Fluency."""
        await self.coach.speak("Final Step: Challenge Round. Sentence Fluency.")
        
        system_prompt = """Generate 1 tricky English sentence for fluency practice.
Return JSON:
{
  "sentence": "string",
  "focus_words": ["word1", "word2"]
}"""
        res = await self.coach.ask_llm("Generate challenge", system_prompt)
        if res and "sentence" in res:
            sentence = res["sentence"]
            if self.coach.transcript_callback:
                self.coach.transcript_callback(f"🏆 Challenge Round\n\nRead this sentence fluently:\n\n\"{sentence}\"")
                
            await self.coach.speak(f"Read this sentence clearly: {sentence}")
            user_speech = await self.coach.listen(duration=12)
            
            # Use LLM to score fluency
            score_prompt = f"User was asked to say: '{sentence}'. They said: '{user_speech}'. Rate fluency (0-100). Return JSON: {{'score': 0-100, 'feedback': 'string'}}"
            score_res = await self.coach.ask_llm("Score fluency", score_prompt)
            if score_res:
                await self.coach.speak(f"Challenge complete! Your fluency score is {score_res['score']}.")
                self.session_data["scores"].append(score_res["score"])

    async def _finish_session(self):
        """Wraps up the session and saves progress."""
        avg_score = sum(self.session_data["scores"]) / len(self.session_data["scores"]) if self.session_data["scores"] else 70
        
        summary = (
            f"Daily Practice Lab complete!\n"
            f"- Drills done: {self.session_data['drills_completed']}\n"
            f"- Accuracy: {self.session_data['correct']}/{self.session_data['total_words']}\n"
        )
        if self.coach.transcript_callback:
            self.coach.transcript_callback(f"📊 Session Complete\n\n{summary}")
            
        await self.coach.speak("Excellent work in the lab today. I've updated your progress tracker.")
        
        # Log to centralized tracker
        progress_tracker.log_session(
            "practice_lab",
            duration_min=10, # Approximate
            words_practiced=self.session_data["total_words"],
            score=avg_score
        )
