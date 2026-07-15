# english_coach/mock_interview.py - AI HR Interviewer (Alina)

import asyncio
import json
import time
from .progress_tracker import progress_tracker

class MockInterview:
    def __init__(self, coach):
        self.coach = coach
        self.interview_history = []
        self.user_info = {}
        self.is_active = False

    async def run(self):
        """Starts a full realistic job interview session with adaptive questions and session looping."""
        while True:
            self.is_active = True
            self.interview_history = []
            
            # 0. Setup Phase (If not already set)
            if not self.user_info.get("name") or not self.user_info.get("role"):
                await self.coach.speak("Welcome to your mock interview. Before we start, what is your name?")
                name_text = await self.coach.listen(duration=8, skip_intent=True)
                self.user_info["name"] = name_text if name_text else "Candidate"
                
                await self.coach.speak(f"Nice to meet you, {self.user_info['name']}. What job role are you applying for today?")
                role_text = await self.coach.listen(duration=10, skip_intent=True)
                self.user_info["role"] = role_text if role_text else "Professional"
                
                await self.coach.speak("And what is your experience level? Beginner, Intermediate, or Experienced?")
                level_text = await self.coach.listen(duration=8, skip_intent=True)
                self.user_info["level"] = level_text if level_text else "Intermediate"

                await self.coach.speak("Would you like 'Practice Mode' with live feedback, or 'Real Interview Mode' for a final report only?")
                mode_text = await self.coach.listen(duration=8, skip_intent=True)
                self.user_info["mode"] = "practice" if mode_text and "practice" in mode_text.lower() else "real"

            await self.coach.speak(f"Excellent. Starting the {self.user_info['mode']} interview for the {self.user_info['role']} position now. Let's begin.")
            await asyncio.sleep(1)

            # 1. Main Interview Loop (5 adaptive questions)
            question_count = 5
            current_q_type = "intro"
            
            for i in range(question_count):
                if not self.coach.is_active: break
                
                # Generate next question using LLM (Adaptive)
                question_data = await self._get_next_question(current_q_type)
                if not question_data: break
                
                question_text = question_data["question"]
                current_q_type = question_data["next_type"]
                
                # Display Question
                if self.coach.transcript_callback:
                    self.coach.transcript_callback(f"💼 **Interview Question {i+1}**\n\n\"{question_text}\"")
                
                await self.coach.speak(question_text)
                
                # Listen to answer
                user_answer = await self.coach.listen(duration=45, skip_intent=True)
                
                if not user_answer or len(user_answer.split()) < 3:
                    await self.coach.speak("I'm sorry, that was a bit brief. Could you please elaborate or explain that in more detail?")
                    user_answer = await self.coach.listen(duration=45, skip_intent=True)
                
                self.interview_history.append({
                    "question": question_text,
                    "answer": user_answer or "[No response]",
                    "type": question_data["type"]
                })

                # Practice Mode Live Feedback
                if self.user_info["mode"] == "practice" and user_answer:
                    await self.coach.speak("Thank you. One quick tip for that answer:")
                    mini_feedback = await self._get_mini_feedback(question_text, user_answer)
                    await self.coach.speak(mini_feedback)
                    await asyncio.sleep(1)
                
                await asyncio.sleep(0.5)

            # 2. Closing
            await self.coach.speak("Thank you. That concludes our interview session. I will now analyze your performance and generate a detailed HR report.")
            
            # 3. Analysis & Report
            analysis = await self._analyze_interview()
            await self._display_report(analysis)
            
            # 4. Save Progress
            if isinstance(analysis, dict) and "error" not in analysis:
                scores = analysis.get("scores", {})
                final_score = scores.get("overall", 0) if isinstance(scores, dict) else 0
                
                progress_tracker.log_session(
                    "mock_interview",
                    duration_min=20,
                    words_practiced=sum(len(h["answer"].split()) for h in self.interview_history),
                    score=final_score,
                    details=analysis
                )

            # 5. Loop Prompt
            await self.coach.speak("Would you like to try another interview for a different role, repeat this session, or exit?")
            loop_res = await self.coach.listen(duration=8, skip_intent=True)
            if not loop_res: break
            
            lr = (loop_res or "").lower()
            if "another" in lr or "new" in lr or "different" in lr:
                self.user_info = {} # Reset to ask everything again
                continue
            elif "again" in lr or "repeat" in lr:
                continue
            else:
                break

    async def _get_next_question(self, q_type):
        """Uses LLM to decide the next best question based on context."""
        context = f"Role: {self.user_info['role']}, Level: {self.user_info['level']}. "
        if self.interview_history:
            last_q = self.interview_history[-1]
            context += f"Last Question: {last_q['question']}, Last Answer: {last_q['answer']}"
        
        system_prompt = f"""You are Alina, a professional HR Manager.
Based on the context, generate the next interview question. 
Ensure it flows naturally from the previous answer if possible (Adaptive).
Types: intro, role_specific, behavioral, situational, follow_up.

Return ONLY JSON:
{{
  "question": "string",
  "type": "string",
  "next_type": "string"
}}"""
        res = await self.coach.ask_llm(f"Generate {q_type} question. Context: {context}", system_prompt)
        return res if res else {"question": "Tell me about your background.", "type": "intro", "next_type": "role_specific"}

    async def _get_mini_feedback(self, question, answer):
        """Quick 1-sentence feedback for Practice Mode."""
        prompt = f"Question: {question}\nAnswer: {answer}\nGive 1 short sentence of professional HR feedback (constructive)."
        res = await self.coach.ask_llm(prompt, "You are Alina, a professional HR Coach.")
        return res.get("feedback", "Good effort, but try to provide more specific examples.") if isinstance(res, dict) else "Good effort."

    async def _analyze_interview(self):
        """Deep analysis of the entire interview transcript."""
        if not self.interview_history:
            return {"error": "Interview was too short."}

        transcript_text = "\n".join([f"Q: {h['question']}\nA: {h['answer']}" for h in self.interview_history])
        
        system_prompt = f"""You are a senior HR Executive. Analyze this interview.
Role: {self.user_info['role']}

Task:
1. Score (0-100): Communication, Confidence, Professionalism, Content.
2. STAR Analysis: Evaluate Situation, Task, Action, Result.
3. Language: Find informal 'weak' words and provide 'impact' words.
4. Answer Improvement: Take the WEAKEST answer and provide a highly professional 'Improved Version'.

Return ONLY JSON:
{{
  "scores": {{
    "overall": 0-100,
    "communication": 0-100,
    "confidence": 0-100,
    "professionalism": 0-100,
    "content": 0-100
  }},
  "star_analysis": {{
    "situation": "feedback", "task": "feedback", "action": "feedback", "result": "feedback"
  }},
  "strengths": ["list"],
  "weaknesses": ["list"],
  "professional_suggestions": [
    {{"informal": "word", "professional": "alternative", "context": "why"}}
  ],
  "improved_answer": {{
    "original": "the weak answer",
    "better": "the professional STAR-based version"
  }},
  "summary": "overall summary"
}}"""
        return await self.coach.ask_llm(f"Analyze interview:\n{transcript_text}", system_prompt)

    async def _display_report(self, analysis):
        if not isinstance(analysis, dict) or "error" in analysis:
            await self.coach.speak("I couldn't generate a report this time. Let's try again later.")
            return

        scores = analysis.get("scores", {})
        star = analysis.get("star_analysis", {})
        
        report_md = (
            f"👔 **Alina's HR Candidate Evaluation**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Candidate:** {self.user_info.get('name', 'User')} | **Role:** {self.user_info.get('role', 'N/A')}\n\n"
            f"📊 **Executive Scorecard:**\n"
            f"• Communication: {scores.get('communication', 0)}/100\n"
            f"• Confidence: {scores.get('confidence', 0)}/100\n"
            f"• Professionalism: {scores.get('professionalism', 0)}/100\n"
            f"• Content Quality: {scores.get('content', 0)}/100\n\n"
            f"🌟 **STAR Method Analysis:**\n"
            f"• **Situation/Task:** {star.get('situation', 'N/A')}\n"
            f"• **Action Taken:** {star.get('action', 'N/A')}\n"
            f"• **Result/Outcome:** {star.get('result', 'N/A')}\n\n"
            f"✅ **Strengths:** {', '.join(analysis.get('strengths', ['N/A'])[:3])}\n"
            f"⚠️ **Areas to Improve:** {', '.join(analysis.get('weaknesses', ['N/A'])[:3])}\n\n"
            f"💼 **Vocabulary Upgrade:**\n"
        )
        
        for sug in analysis.get("professional_suggestions", [])[:2]:
            if isinstance(sug, dict):
                report_md += f"❌ '{sug.get('informal')}' → ✅ **'{sug.get('professional')}'**\n"

        improved = analysis.get("improved_answer")
        if improved and isinstance(improved, dict):
            orig = improved.get("original", "")
            better = improved.get("better", "")
            if orig and better:
                report_md += (
                    f"\n💡 **Interview Answer Polish:**\n"
                    f"**You said:** \"{orig}\"\n"
                    f"**HR Version:** \"{better}\"\n"
                )

        report_md += f"\n📝 **HR Final Verdict:** {analysis.get('summary', 'Candidate shows good potential.')}"

        if self.coach.transcript_callback:
            self.coach.transcript_callback(report_md)

        await self.coach.speak(f"Interview complete! I've shared your HR evaluation report. {analysis.get('summary', '')}")
