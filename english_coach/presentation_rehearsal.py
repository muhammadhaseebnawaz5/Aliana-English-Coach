# english_coach/presentation_rehearsal.py - Formal Presentation Practice Module

import asyncio
import time
import re
import json
import random
from datetime import datetime
from .progress_tracker import progress_tracker

class PresentationRehearsal:
    def __init__(self, coach):
        self.coach = coach
        self.is_running = False
        self.full_transcript = ""
        self.filler_words = ["um", "uh", "err", "ah", "like", "basically", "you know", "actually", "sort of", "kind of"]

    async def run(self, topic=None):
        """Starts the presentation rehearsal workflow."""
        while True:
            # 0. Topic Selection
            if not topic:
                # Get used topics from tracker to avoid repetition
                used_topics = progress_tracker.data.get("used_presentation_topics", [])
                
                await self.coach.speak("What is the topic of your presentation today? You can provide your own topic, or say 'any' for a random professional suggestion.")
                topic_input = await self.coach.listen(duration=10, skip_intent=True)
                
                ti = (topic_input or "").lower()
                if not topic_input or "any" in ti or "suggest" in ti or "choice" in ti or "choose" in ti:
                    await self.coach.speak("Let me think of a fresh professional topic for you...")
                    system = f"""Generate ONE unique, professional presentation topic for an English learner.
    EXCLUDE these previously used topics: {used_topics}
    The topic should be engaging and useful for professional development.
    Return ONLY JSON: {{"topic": "The Topic Title"}}"""
                    res = await self.coach.ask_llm("Suggest a new presentation topic.", system)
                    if res and isinstance(res, dict):
                        topic = res.get("topic", "The Future of Remote Work")
                    else:
                        topic = "Effective Workplace Communication"
                else:
                    # Clean up the user topic (e.g., "I want to talk about AI" -> "Artificial Intelligence")
                    await self.coach.speak("Got it. Let me prepare the rehearsal for that.")
                    system = "Extract the core topic name from the user's request. Return ONLY the topic (1-4 words). Example: 'I want to talk about climate change' -> 'Climate Change Impact'"
                    res = await self.coach.ask_llm(topic_input, system)
                    if res and isinstance(res, dict) and res.get("topic"):
                        topic = res.get("topic")
                    else:
                        topic = topic_input[:50] # Fallback to first 50 chars

            # Record this topic as used
            if topic:
                progress_tracker.add_used_topic(topic)

            # 1. Instructions
            duration_sec = self.coach.speaking_duration * 4 # Standard 1 min for rehearsal
            intro_text = (
                f"🎤 **Presentation Rehearsal: {topic}**\n\n"
                f"Goal: Practice speaking clearly and professionally for **{duration_sec // 60} minutes**.\n\n"
                "Rules:\n"
                "- Watch the live timer.\n"
                "- Your speech will appear live as 'subtitles'.\n"
                "- A detailed analysis report will be generated at the end."
            )
            if self.coach.transcript_callback:
                self.coach.transcript_callback(intro_text)
                
            await self.coach.speak(f"Alright, let's start your presentation on {topic}. You have {duration_sec // 60} minutes. Please begin when you're ready.")

            # 2. Setup Live UI Updates
            original_callback = self.coach.on_transcription_callback
            def live_subtitle(text):
                if self.coach.transcript_callback:
                    rem = getattr(self, 'remaining_time', duration_sec)
                    if rem is None: rem = 0
                    m, s = divmod(int(rem), 60)
                    timer_str = f"⏱️ {m:02d}:{s:02d}"
                    self.coach.transcript_callback(f"{timer_str} | 🎤 Presentation: {topic}\n\n🎤 **Live Subtitles:**\n{text}")
                if original_callback:
                    original_callback(text)

            self.coach.on_transcription_callback = live_subtitle
            self.is_running = True

            # 3. Timer Task
            timer_task = asyncio.create_task(self._run_timer(duration_sec))
            
            try:
                # 4. Recording Session
                self.full_transcript = await self.coach.listen(duration=duration_sec, skip_intent=True)
            finally:
                self.is_running = False
                timer_task.cancel()
                self.coach.on_transcription_callback = original_callback

            # 5. Analysis & Report
            await self.coach.speak("Presentation complete. Analyzing your performance scorecard.")
            
            analysis = await self._analyze_presentation(self.full_transcript, duration_sec)
            await self._display_report(analysis)
            
            # Save progress
            if isinstance(analysis, dict) and "error" not in analysis:
                scores = analysis.get("scores", {})
                prof_score = 0
                if isinstance(scores, dict):
                    prof_score = scores.get("professionalism", 0)
                
                progress_tracker.log_session(
                    "presentation_rehearsal",
                    duration_min=duration_sec/60,
                    words_practiced=len(self.full_transcript.split()),
                    score=prof_score,
                    details=analysis
                )
                if isinstance(analysis, dict) and analysis.get("filler_count"):
                    progress_tracker.add_filler_count(analysis["filler_count"])

            # 6. Loop Prompt
            await self.coach.speak("Would you like to rehearse another topic, try this one again, or return home?")
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
        """Updates the remaining time for UI feedback."""
        self.remaining_time = total_sec
        while self.remaining_time > 0 and self.is_running:
            await asyncio.sleep(1)
            self.remaining_time -= 1

    async def _analyze_presentation(self, transcript, duration_sec):
        """Detailed analysis using metrics and LLM."""
        if not transcript or len(transcript.strip()) < 10:
            return {"error": "Too little speech to analyze."}

        # Basic Metrics
        words = transcript.split()
        word_count = len(words)
        wpm = round((word_count / duration_sec) * 60)
        
        # Filler Detection (Regex)
        filler_found = []
        for f in self.filler_words:
            matches = re.findall(rf"\b{f}\b", transcript, re.IGNORECASE)
            if matches:
                filler_found.append({"word": f, "count": len(matches)})
        
        total_fillers = sum(f["count"] for f in filler_found)

        # Advanced Analysis via LLM
        system_prompt = f"""You are a professional Speech & Presentation Analyst.
Analyze the following transcript of a {duration_sec/60} minute presentation.

Transcript: "{transcript}"

Provide a detailed analysis in JSON:
{{
  "scores": {{
    "confidence": 0-100,
    "fluency": 0-100,
    "clarity": 0-100,
    "professionalism": 0-100
  }},
  "qualitative_feedback": {{
    "confidence": "string",
    "fluency": "string",
    "professionalism": "string",
    "clarity": "string"
  }},
  "filler_analysis": "string feedback about filler words used",
  "professional_suggestions": [
    {{"informal": "word used", "professional": "suggested alternative", "context": "why"}}
  ],
  "improved_excerpt": {{
    "original": "a confusing or informal sentence from transcript",
    "better": "the polished professional version"
  }},
  "section_feedback": {{
    "start": "feedback on introduction",
    "middle": "feedback on body/explanation",
    "end": "feedback on conclusion"
  }},
  "keywords": {{
    "strong": ["list", "of", "impressive", "words", "used"],
    "overused": ["list", "of", "words", "repeated", "too", "much"]
  }}
}}"""

        llm_analysis = await self.coach.ask_llm("Analyze presentation", system_prompt)
        if not llm_analysis:
            llm_analysis = {
                "scores": {"confidence": 70, "fluency": 70, "clarity": 70, "professionalism": 70},
                "qualitative_feedback": {"confidence": "Good.", "fluency": "Good.", "professionalism": "Good.", "clarity": "Good."},
                "filler_analysis": "None",
                "professional_suggestions": [],
                "improved_excerpt": {"original": "", "better": ""},
                "section_feedback": {"start": "", "middle": "", "end": ""},
                "keywords": {"strong": [], "overused": []}
            }
        
        # Combine metrics
        report = {
            "duration": f"{duration_sec//60}:{duration_sec%60:02d}",
            "word_count": word_count,
            "wpm": wpm,
            "filler_count": total_fillers,
            "fillers_detected": filler_found,
            **llm_analysis
        }
        
        return report

    async def _display_report(self, analysis):
        """Format and show the final report."""
        if not analysis or "error" in analysis:
            await self.coach.speak(analysis.get("error", "Analysis failed.") if isinstance(analysis, dict) else "Analysis failed.")
            return

        scores = analysis.get("scores", {})
        if not isinstance(scores, dict): scores = {}
        
        report_md = (
            f"🎤 **Presentation Speaker Scorecard**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Time Management:** {analysis.get('duration', '0:00')} | **Pace:** {analysis.get('wpm', 0)} WPM\n\n"
            f"🏆 **Performance Ratings:**\n"
            f"• **Confidence:** {scores.get('confidence', 0)}/100\n"
            f"• **Clarity:** {scores.get('clarity', 0)}/100\n"
            f"• **Professionalism:** {scores.get('professionalism', 0)}/100\n\n"
            f"👥 **Audience Impact:**\n"
            f"- **Flow:** {analysis.get('qualitative_feedback', {}).get('fluency', 'Good flow.')}\n"
            f"- **Filler Impact:** {analysis.get('filler_count', 0)} fillers detected. {analysis.get('filler_analysis', '')}\n\n"
            f"🛠️ **Professional Upgrades:**\n"
        )
        
        # Add a few top suggestions
        for sug in analysis.get("professional_suggestions", [])[:3]:
            if isinstance(sug, dict) and "informal" in sug and "professional" in sug:
                report_md += f"🔸 Replace *'{sug['informal']}'* with **'{sug['professional']}'**.\n"

        improved = analysis.get("improved_excerpt")
        if improved and isinstance(improved, dict) and improved.get("original"):
            report_md += (
                f"\n🌟 **Polished Highlight:**\n"
                f"**Original:** \"{improved.get('original')}\"\n"
                f"**Polished:** \"{improved.get('better')}\"\n"
            )

        # Section Feedback
        sf = analysis.get("section_feedback", {})
        if isinstance(sf, dict) and sf.get("start"):
            report_md += f"\n📌 **Key Section Advice:**\n- **Intro:** {sf.get('start')}\n- **Conclusion:** {sf.get('end')}\n"

        if self.coach.transcript_callback:
            self.coach.transcript_callback(report_md)

        # Spoken Summary
        spoken_summary = (
            f"Your presentation rehearsal is complete. Your overall professionalism score is {scores.get('professionalism', 0)} percent. "
            f"One key takeaway: {analysis.get('qualitative_feedback', {}).get('professionalism', 'Keep your confidence high!')}"
        )
        await self.coach.speak(spoken_summary)

    def _get_speed_label(self, wpm):
        if wpm < 110: return "Slow"
        if wpm > 160: return "Fast"
        return "Ideal"
