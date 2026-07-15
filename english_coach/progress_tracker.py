# english_coach/progress_tracker.py - Persistent English Learning Progress
# Tracks weak words, grammar mistakes, interview answers, session history

import json
import os
import time
from core import config


class ProgressTracker:
    """Persistent storage for English learning progress across all modules."""

    def __init__(self):
        self.data_path = config.ENGLISH_COACH_DATA
        self.data = self._load()

    def _load(self):
        """Load progress from disk."""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default_data()

    def _default_data(self):
        return {
            "weak_words": [],
            "improved_words": [],
            "used_presentation_topics": [],
            "grammar_mistakes": [],
            "interview_answers": {},
            "sessions": [],
            "streak": {"current": 0, "last_date": None},
            "stats": {
                "total_sessions": 0,
                "total_words": 0,
                "overall_accuracy": 0,
                "module_stats": {
                    "practice_lab": {"sessions": 0, "avg_score": 0, "words": 0},
                    "pronunciation_drill": {"sessions": 0, "avg_score": 0, "words": 0},
                    "presentation_rehearsal": {"sessions": 0, "avg_score": 0, "fluency": 0, "confidence": 0, "professionalism": 0},
                    "mock_interview": {"sessions": 0, "avg_score": 0},
                    "casual_conversation": {"sessions": 0, "avg_score": 0}
                },
                "filler_word_trend": [],
                "pronunciation_scores": []
            }
        }

    def save(self):
        """Persist progress to disk."""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    # ── Weak Words (Cross-Module Intelligence) ────────────────
    def add_weak_word(self, word):
        """Add a word that needs more practice. Used by all modules."""
        word = word.lower().strip()
        if word not in self.data["weak_words"]:
            self.data["weak_words"].append(word)
            if word in self.data["improved_words"]:
                self.data["improved_words"].remove(word)
            self.save()

    def mark_word_improved(self, word):
        """Move a word from weak to improved."""
        word = word.lower().strip()
        if word in self.data["weak_words"]:
            self.data["weak_words"].remove(word)
        if word not in self.data["improved_words"]:
            self.data["improved_words"].append(word)
        self.save()

    def get_weak_words(self, n=10):
        """Get weak words to be reintroduced in Practice Lab or Drills."""
        return self.data["weak_words"][:n]

    # ── Sessions & Stats ──────────────────────────
    def log_session(self, module_name, duration_min=0, words_practiced=0, score=0, details=None):
        """Log a session and update centralized stats."""
        today = time.strftime("%Y-%m-%d")
        
        # 1. Update Streak
        if self.data["streak"]["last_date"] != today:
            if self.data["streak"]["last_date"] == time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)):
                self.data["streak"]["current"] += 1
            else:
                self.data["streak"]["current"] = 1
            self.data["streak"]["last_date"] = today

        # 2. Log Session Entry
        session = {
            "date": today,
            "time": time.strftime("%H:%M"),
            "module": module_name,
            "duration_min": duration_min,
            "words_practiced": words_practiced,
            "score": score
        }
        if details:
            session["details"] = details
        self.data["sessions"].append(session)
        
        # 3. Update Module Stats
        m_stats = self.data["stats"]["module_stats"].get(module_name)
        if m_stats:
            m_stats["sessions"] += 1
            # Update moving average score
            m_stats["avg_score"] = round(((m_stats["avg_score"] * (m_stats["sessions"] - 1)) + score) / m_stats["sessions"])
            if "words" in m_stats:
                m_stats["words"] += words_practiced
            
            # Update module-specific advanced metrics if present in details
            if details:
                for metric in ["fluency", "confidence", "professionalism"]:
                    if metric in details.get("scores", {}) and metric in m_stats:
                        m_stats[metric] = round(((m_stats[metric] * (m_stats["sessions"] - 1)) + details["scores"][metric]) / m_stats["sessions"])

        # 4. Global Stats
        self.data["stats"]["total_sessions"] += 1
        self.data["stats"]["total_words"] += words_practiced
        
        # Keep last 100 sessions
        self.data["sessions"] = self.data["sessions"][-100:]
        self.save()

    def get_progress_report(self):
        """Generate a comprehensive progress report across all skills."""
        stats = self.data["stats"]
        m_stats = stats["module_stats"]
        
        report = (
            f"📈 **Complete Speaking Progress Report**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 Daily Streak: {self.data['streak']['current']} days\n"
            f"🎯 Total Sessions: {stats['total_sessions']} | 📝 Total Words: {stats['total_words']}\n\n"
            f"**Module Breakdown:**\n"
            f"- Practice Lab: {m_stats['practice_lab']['avg_score']}% accuracy\n"
            f"- Pronunciation: {m_stats['pronunciation_drill']['avg_score']}% accuracy\n"
            f"- Presentation: {m_stats['presentation_rehearsal']['avg_score']}% (Fluency: {m_stats['presentation_rehearsal']['fluency']}%, Confidence: {m_stats['presentation_rehearsal']['confidence']}%)\n\n"
            f"**Weak Areas:**\n"
        )
        
        weak_words = stats.get("weak_words", [])
        if weak_words:
            report += f"- Vocabulary: {len(weak_words)} words need practice.\n"
        
        # Qualitative logic
        if m_stats['presentation_rehearsal']['fluency'] < 70:
            report += "- Flow: You need to improve fluency and reduce hesitation in formal speech.\n"
        if m_stats['presentation_rehearsal']['professionalism'] < 70:
            report += "- Style: Focus on using more professional vocabulary in presentations.\n"
            
        report += "\n**Suggested Next Step:** Start a 'Practice Lab' session to focus on weak words."
        return report

    # ── Helpers ───────────────────────────────────
    def add_filler_count(self, count):
        self.data["stats"]["filler_word_trend"].append(count)
        self.data["stats"]["filler_word_trend"] = self.data["stats"]["filler_word_trend"][-20:]
        self.save()

    def add_used_topic(self, topic):
        if "used_presentation_topics" not in self.data:
            self.data["used_presentation_topics"] = []
        if topic not in self.data["used_presentation_topics"]:
            self.data["used_presentation_topics"].append(topic)
            self.save()

    def save_session_state(self, mode, sub_state=None):
        self.data["last_session_mode"] = mode
        self.data["last_session_sub_state"] = sub_state
        self.save()

    def load_session_state(self):
        return {"mode": self.data.get("last_session_mode"), "sub_state": self.data.get("last_session_sub_state")}

    def add_grammar_mistake(self, mistake):
        if mistake not in self.data["grammar_mistakes"]:
            self.data["grammar_mistakes"].append(mistake)
            self.data["grammar_mistakes"] = self.data["grammar_mistakes"][-10:]
            self.save()

    def log_mistake(self, original_text, corrected_text, context=""):
        log_file = os.path.join(os.path.dirname(self.data_path), "mistakes_log.txt")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {context}\n")
                f.write(f"You said: {original_text}\nCorrection: {corrected_text}\n" + "-" * 40 + "\n")
        except Exception: pass

    def save_interview_answer(self, k, a):
        self.data["interview_answers"][k] = {"answer": a, "updated": time.strftime("%Y-%m-%d")}
        self.save()

    def get_weekly_summary(self):
        return f"Streak: {self.data['streak']['current']} days. Weak words: {len(self.data['weak_words'])}."

progress_tracker = ProgressTracker()


# Global singleton
progress_tracker = ProgressTracker()
