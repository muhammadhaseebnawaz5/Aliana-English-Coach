import sys
import os
# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import math
import random
import time
import asyncio
import threading
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QStackedWidget,
    QScrollArea,
    QSlider,
    QGridLayout,
    QSpacerItem,
    QLineEdit,
    QDialog,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
    QRectF,
    QSize,
    QRect,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QLinearGradient,
    QRadialGradient,
    QFont,
    QPainterPath,
    QPalette,
)

from core.brain import StandaloneBrain
from english_coach.coach_engine import CoachEngine
from english_coach.progress_tracker import progress_tracker
from core import config

# ═══════════════════════════════════════════════════════════════════
#  DESIGN TOKENS (Shared with alina_ui.py)
# ═══════════════════════════════════════════════════════════════════

C = {
    "bg": "#080B12",
    "bg2": "#0E1220",
    "bg3": "#141826",
    "card": "#161C2E",
    "card2": "#1C2338",
    "border": "#252D45",
    "border2": "#2E3855",
    "alina": "#A78BFA",
    "alina2": "#7C3AED",
    "alina_dim": "#A78BFA22",
    "alina_glow": "#A78BFA44",
    "teal": "#2DD4BF",
    "teal_dim": "#2DD4BF22",
    "coral": "#FB7185",
    "coral_dim": "#FB718522",
    "amber": "#FBBF24",
    "amber_dim": "#FBBF2422",
    "green": "#34D399",
    "green_dim": "#34D39922",
    "blue": "#60A5FA",
    "blue_dim": "#60A5FA22",
    "text": "#E2E8F8",
    "text2": "#94A3C4",
    "text3": "#4B5880",
    "text_dim": "#1E2640",
}

MODES = [
    {
        "key": "daily",
        "icon": "📅",
        "label": "Daily Routine",
        "sub": "4 steps · Warm-up → Speaking → Pronunciation → Interview",
        "color": C["alina"],
        "dim": C["alina_dim"],
    },
    {
        "key": "speaking",
        "icon": "🗣",
        "label": "Speaking Practice",
        "sub": "Talk freely on any topic. Real-time corrections.",
        "color": C["teal"],
        "dim": C["teal_dim"],
    },
    {
        "key": "pronunciation",
        "icon": "🎯",
        "label": "Pronunciation Drill",
        "sub": "Difficult words. Instant accuracy feedback.",
        "color": C["green"],
        "dim": C["green_dim"],
    },
    {
        "key": "interview",
        "icon": "👔",
        "label": "Mock Interview",
        "sub": "Alina as HR Manager. Professional Q&A session.",
        "color": C["coral"],
        "dim": C["coral_dim"],
    },
    {
        "key": "presentation",
        "icon": "🎤",
        "label": "Presentation",
        "sub": "3-minute rehearsal. Live timer and filler word detection.",
        "color": C["blue"],
        "dim": C["blue_dim"],
    },
    {
        "key": "chat",
        "icon": "💬",
        "label": "Casual Chat",
        "sub": "Normal gupshup. Short, natural, friendly replies.",
        "color": C["amber"],
        "dim": C["amber_dim"],
    },
    {
        "key": "practice",
        "icon": "🧪",
        "label": "Practice Lab",
        "sub": "Quick daily drills. Focus on repetition and speed.",
        "color": C["blue"],
        "dim": C["blue_dim"],
    },
    {
        "key": "progress",
        "icon": "📊",
        "label": "My Progress",
        "sub": "Scores, weak words, grammar history, 5-day plan.",
        "color": C["blue"],
        "dim": C["blue_dim"],
    },
]

# ═══════════════════════════════════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════

class WaveformWidget(QWidget):
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.bars = 32
        self.heights = [0.05] * self.bars
        self.target = [0.05] * self.bars
        self.active = False
        self.setFixedHeight(52)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_active(self, on: bool):
        self.active = on
        if not on:
            self.target = [0.05] * self.bars
        self.update()

    def _tick(self):
        if self.active:
            for i in range(self.bars):
                self.target[i] = random.uniform(0.08, 1.0)
        for i in range(self.bars):
            self.heights[i] += (self.target[i] - self.heights[i]) * 0.25
        self.update()

    def paintEvent(self, a0):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bw = max(2, (w // self.bars) - 2)
        gap = (w - bw * self.bars) / (self.bars + 1)
        for i, ht in enumerate(self.heights):
            x = gap + i * (bw + gap)
            bh = max(3, ht * (h - 8))
            y = (h - bh) / 2
            alpha = int(80 + ht * 175)
            c = QColor(self.color)
            c.setAlpha(alpha)
            grad = QLinearGradient(x, y, x, y + bh)
            top = QColor(self.color)
            top.setAlpha(alpha)
            bot = QColor(self.color)
            bot.setAlpha(alpha // 3)
            grad.setColorAt(0, top)
            grad.setColorAt(1, bot)
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(int(x), int(y), bw, int(bh), bw // 2, bw // 2)
        p.end()

class MicButton(QWidget):
    clicked = pyqtSignal()
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.listening = False
        self.ring_r = 0.0
        self.ring_a = 0
        self.setFixedSize(120, 120)
        self._ring_timer = QTimer(self)
        self._ring_timer.timeout.connect(self._ring_tick)

    def set_listening(self, on: bool):
        self.listening = on
        if on: self._ring_timer.start(30)
        else:
            self._ring_timer.stop()
            self.ring_r = 0.0
        self.update()

    def _ring_tick(self):
        self.ring_r = (self.ring_r + 1.2) % 60
        self.ring_a = max(0, int(200 * (1 - self.ring_r / 60)))
        self.update()

    def mousePressEvent(self, a0):
        if self.listening:
            self.clicked.emit()
        super().mousePressEvent(a0)

    def paintEvent(self, a0):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        base_r = 46
        if self.listening and self.ring_r > 0:
            rc = QColor(self.color)
            rc.setAlpha(self.ring_a)
            p.setPen(QPen(rc, 2))
            rr = base_r + self.ring_r
            p.drawEllipse(QRectF(cx - rr, cy - rr, rr * 2, rr * 2))
        if self.listening:
            gc = QColor(self.color)
            gc.setAlpha(20)
            p.setBrush(gc)
            p.setPen(Qt.PenStyle.NoPen)
            gr = base_r + 10
            p.drawEllipse(QRectF(cx - gr, cy - gr, gr * 2, gr * 2))
        grad = QRadialGradient(cx - 8, cy - 8, base_r * 1.4)
        grad.setColorAt(0, QColor(self.color).lighter(130))
        grad.setColorAt(1, QColor(self.color))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - base_r, cy - base_r, base_r * 2, base_r * 2))
        p.setPen(QPen(QColor("#FFFFFF"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        mw, mh, mr = 13, 20, 6
        mx, my = cx - mw / 2, cy - mh / 2 - 3
        path = QPainterPath()
        path.addRoundedRect(QRectF(mx, my, mw, mh), mr, mr)
        p.drawPath(path)
        p.drawArc(QRectF(cx-11, cy+3, 22, 14), 0, -180*16)
        p.drawLine(int(cx), int(cy+16), int(cx), int(cy+21))
        p.drawLine(int(cx-6), int(cy+21), int(cx+6), int(cy+21))
        p.end()

class AlinaAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speaking = False
        self.mouth_open = 0.0
        self.blink = 1.0
        self._blink_dir = -1
        self.setFixedSize(90, 90)
        self._talk_t = QTimer(self)
        self._talk_t.timeout.connect(self._talk_tick)
        self._blink_t = QTimer(self)
        self._blink_t.timeout.connect(self._blink_tick)
        self._blink_t.start(60)
        self._schedule_blink()

    def set_speaking(self, on: bool):
        self.speaking = on
        if on: self._talk_t.start(60)
        else:
            self._talk_t.stop()
            self.mouth_open = 0.0
        self.update()

    def _talk_tick(self):
        self.mouth_open = abs(math.sin(time.time() * 8)) * 0.9
        self.update()

    def _schedule_blink(self):
        QTimer.singleShot(random.randint(2000, 5000), self._start_blink)

    def _start_blink(self):
        self._blink_dir = -1

    def _blink_tick(self):
        if self._blink_dir == -1:
            self.blink = max(0.0, self.blink - 0.25)
            if self.blink == 0.0: self._blink_dir = 1
        elif self._blink_dir == 1:
            self.blink = min(1.0, self.blink + 0.25)
            if self.blink == 1.0:
                self._blink_dir = 0
                self._schedule_blink()
        self.update()

    def paintEvent(self, a0):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r = 45, 45, 38
        if self.speaking:
            gc = QColor("#A78BFA")
            gc.setAlpha(30)
            p.setBrush(gc)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - r - 5, cy - r - 5, (r + 5) * 2, (r + 5) * 2))
        grad = QRadialGradient(cx - 5, cy - 8, r)
        grad.setColorAt(0, QColor("#2A1F4E")); grad.setColorAt(1, QColor("#13102A"))
        p.setBrush(QBrush(grad)); p.setPen(QPen(QColor("#A78BFA"), 1.5))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        ey = cy - 8
        for ex in [cx - 11, cx + 11]:
            eye_h = max(1, int(9 * self.blink))
            p.setBrush(QColor("#E2E8F8")); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRect(ex - 5, ey - eye_h // 2, 10, eye_h))
        mo = self.mouth_open
        mouth_w, mouth_y = 18, cy + 10
        p.setBrush(QColor("#1A0A2E") if mo > 0.1 else Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#E2E8F8"), 1.5))
        mh = max(2, int(mo * 10))
        p.drawRoundedRect(QRect(cx - mouth_w // 2, mouth_y - mh // 2, mouth_w, max(4, mh)), 4, 4)
        p.end()

class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool, accent: str, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.accent = accent
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10); lay.setSpacing(4)
        who = QLabel("You" if is_user else "Alina")
        who.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        who.setStyleSheet(f"color: {'#94A3C4' if is_user else accent};")
        lay.addWidget(who)
        self.body = QLabel(text)
        self.body.setWordWrap(True); self.body.setFont(QFont("Segoe UI", 11))
        self.body.setStyleSheet(f"color: {C['text']}; line-height: 160%;")
        lay.addWidget(self.body)
        bg = "#1A2545" if is_user else "#1A1630"
        border = "border-left: 2px solid #2E3855;" if is_user else f"border-left: 3px solid {accent};"
        self.setStyleSheet(f"QFrame {{ background: {bg}; {border} border-radius: 12px; }}")

    def update_text(self, text):
        self.body.setText(text)
        # Ensure it scrolls to bottom after text change if needed
        p = self.parentWidget()
        if p:
            lay_w = p.parentWidget()
            if lay_w:
                scroll = lay_w.parentWidget() # QScrollArea
                if scroll and hasattr(scroll, "verticalScrollBar"):
                    sb = scroll.verticalScrollBar()
                    if sb: sb.setValue(sb.maximum())

class NavBar(QWidget):
    mode_selected = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(72); self._active = 0; self._btns = []
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 16, 8, 16); lay.setSpacing(4)
        self.logo_btn = QPushButton("A")
        self.logo_btn.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logo_btn.setStyleSheet(f"QPushButton {{ color: {C['alina']}; background: transparent; border: none; margin-bottom: 16px; }}")
        self.logo_btn.clicked.connect(lambda: self.mode_selected.emit(-1))
        lay.addWidget(self.logo_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        for i, m in enumerate(MODES):
            btn = QPushButton(m["icon"]); btn.setFixedSize(50, 50); btn.setFont(QFont("Segoe UI Emoji", 18))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select(idx))
            self._btns.append(btn); lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(); self.setStyleSheet(f"QWidget {{ background: {C['bg2']}; border-right: 1px solid {C['border']}; }}")
        self._refresh()

    def _select(self, idx: int):
        self._active = idx; self._refresh(); self.mode_selected.emit(idx)

    def _refresh(self):
        for i, btn in enumerate(self._btns):
            m = MODES[i]
            if i == self._active:
                btn.setStyleSheet(f"QPushButton {{ background: {m['dim']}; border: 1px solid {m['color']}55; border-radius: 14px; color: {m['color']}; }}")
            else:
                btn.setStyleSheet(f"QPushButton {{ background: transparent; border: 1px solid transparent; border-radius: 14px; color: {C['text3']}; }} "
                                  f"QPushButton:hover {{ background: {m['dim']}; color: {m['color']}; border: 1px solid {m['color']}33; }}")

# ═══════════════════════════════════════════════════════════════════
#  SCREENS
# ═══════════════════════════════════════════════════════════════════

class HomeScreen(QWidget):
    start_mode = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self); root.setContentsMargins(28, 24, 28, 24); root.setSpacing(20)
        top = QHBoxLayout(); top.addWidget(AlinaAvatar())
        intro = QVBoxLayout(); intro.setSpacing(2)
        name_lbl = QLabel("Hi, I'm Alina 👋"); name_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {C['text']};")
        sub_lbl = QLabel("Your personal English voice coach. Let's practice!"); sub_lbl.setFont(QFont("Segoe UI", 11))
        sub_lbl.setStyleSheet(f"color: {C['text2']};")
        intro.addWidget(name_lbl); intro.addWidget(sub_lbl); top.addLayout(intro); top.addStretch()
        
        # Stats from ProgressTracker
        total = progress_tracker.data["stats"]["total_sessions"]
        words = sum(s.get("words_practiced", 0) for s in progress_tracker.data["sessions"])
        top.addWidget(self._pill(f"🔥  Sessions: {total}"))
        top.addWidget(self._pill(f"⏱  Words: {words}"))
        root.addLayout(top)

        div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background: {C['border']};"); root.addWidget(div)
        
        # Daily card
        daily = QFrame(); daily.setStyleSheet(f"QFrame {{ background: {C['card']}; border: 1px solid {C['alina']}55; border-radius: 16px; }}")
        dlay = QHBoxLayout(daily); dlay.setContentsMargins(20, 16, 20, 16)
        lbl_date = QLabel("📅")
        lbl_date.setFont(QFont("Segoe UI Emoji", 28))
        dlay.addWidget(lbl_date)
        info = QVBoxLayout(); info.setSpacing(4)
        lbl_title = QLabel("Today's Daily Routine")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        lbl_title.setStyleSheet(f"color: {C['text']};")
        info.addWidget(lbl_title)
        lbl_sub = QLabel("4 steps · Warm-up → Speaking → Pronunciation → Interview")
        lbl_sub.setFont(QFont("Segoe UI", 10))
        lbl_sub.setStyleSheet(f"color: {C['text2']};")
        info.addWidget(lbl_sub)
        dlay.addLayout(info); dlay.addStretch()
        go = QPushButton("Start →")
        go.setCursor(Qt.CursorShape.PointingHandCursor)
        go.setStyleSheet(f"QPushButton {{ background: {C['alina']}; color: #0D0A1E; border-radius: 10px; padding: 8px 18px; }} QPushButton:hover {{ background: #BDB0FC; }}")
        go.clicked.connect(lambda: self.start_mode.emit(0))
        dlay.addWidget(go); root.addWidget(daily)

        lbl_pm = QLabel("Practice modes")
        lbl_pm.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        lbl_pm.setStyleSheet(f"color: {C['text3']}; letter-spacing: 2px;")
        root.addWidget(lbl_pm)
        grid = QGridLayout(); grid.setSpacing(10)
        for i, m in enumerate(MODES[1:], 1):
            card = QFrame(); card.setCursor(Qt.CursorShape.PointingHandCursor); card.setMinimumHeight(110)
            card.setStyleSheet(f"QFrame {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px; }} QFrame:hover {{ background: {m['dim']}; border: 1px solid {m['color']}66; }}")
            clay = QVBoxLayout(card); clay.setContentsMargins(16, 14, 16, 14); clay.setSpacing(6)
            card_ic = QLabel(m["icon"])
            card_ic.setFont(QFont("Segoe UI Emoji", 22))
            clay.addWidget(card_ic)
            card_lbl = QLabel(m["label"])
            card_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            card_lbl.setStyleSheet(f"color: {C['text']};")
            clay.addWidget(card_lbl)
            card_sub = QLabel(m["sub"])
            card_sub.setFont(QFont("Segoe UI", 9))
            card_sub.setStyleSheet(f"color: {C['text2']};")
            card_sub.setWordWrap(True)
            clay.addWidget(card_sub)
            grid.addWidget(card, (i - 1) // 3, (i - 1) % 3)
            card.mousePressEvent = lambda a0, idx=i: self.start_mode.emit(idx)
        root.addLayout(grid); root.addStretch()

    def _pill(self, text: str):
        l = QLabel(text)
        l.setFont(QFont("Segoe UI", 10))
        l.setStyleSheet(f"color: {C['text2']}; background: {C['card']}; border: 1px solid {C['border']}; border-radius: 16px; padding: 5px 14px;")
        return l

class SessionScreen(QWidget):
    back_clicked = pyqtSignal()
    def __init__(self, mode_idx: int = 1, parent=None):
        super().__init__(parent)
        self.mode = MODES[mode_idx]
        self.setStyleSheet(f"background: {C['bg']};")
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        
        hdr = QFrame(); hdr.setFixedHeight(60); hdr.setStyleSheet(f"background: {C['bg2']}; border-bottom: 1px solid {C['border']};")
        hlay = QHBoxLayout(hdr); hlay.setContentsMargins(16, 0, 16, 0)
        back = QPushButton("← Back")
        back.setFont(QFont("Segoe UI", 10))
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(f"color: {C['text2']}; border: none;")
        back.clicked.connect(self.back_clicked.emit); hlay.addWidget(back)
        lbl_mode = QLabel("  " + self.mode['icon'] + "  " + self.mode['label'])
        lbl_mode.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        lbl_mode.setStyleSheet(f"color: {C['text']};")
        hlay.addWidget(lbl_mode)
        hlay.addStretch(); root.addWidget(hdr)

        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(True); self.scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background: {C['bg']}; }} QScrollBar {{ width: 4px; }}")
        self._chat_w = QWidget(); self._chat_lay = QVBoxLayout(self._chat_w); self._chat_lay.setContentsMargins(20, 16, 20, 16); self._chat_lay.setSpacing(14); self._chat_lay.addStretch()
        self.scroll_area.setWidget(self._chat_w); root.addWidget(self.scroll_area, 1)

        vp = QFrame(); vp.setStyleSheet(f"background: {C['bg2']}; border-top: 1px solid {C['border']};")
        vlay = QVBoxLayout(vp); vlay.setContentsMargins(20, 14, 20, 14); vlay.setSpacing(12)
        self.wave = WaveformWidget(self.mode["color"]); vlay.addWidget(self.wave)
        mid_row = QHBoxLayout()
        lc = QVBoxLayout(); self.avatar = AlinaAvatar()
        self.st_lbl = QLabel("Ready")
        self.st_lbl.setFont(QFont("Segoe UI", 10))
        self.st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.st_lbl.setStyleSheet(f"color: {C['text2']};")
        
        # Transcription preview card
        self.trans_card = QFrame()
        self.trans_card.setStyleSheet(f"QFrame {{ background: #1A1630; border-left: 3px solid {self.mode['color']}; border-radius: 12px; }}")
        self.trans_card.setFixedWidth(300)
        self.trans_card.hide()
        self.trans_lay = QVBoxLayout(self.trans_card)
        self.trans_lay.setContentsMargins(14, 10, 14, 10); self.trans_lay.setSpacing(4)
        
        self.trans_hdr = QLabel("🎙 Listening...")
        self.trans_hdr.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.trans_hdr.setStyleSheet(f"color: {self.mode['color']};")
        self.trans_lay.addWidget(self.trans_hdr)
        # Deleted trans_lbl from here as per user request to only show status
        
        self.cur_user_bubble = None

        lc.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        lc.addWidget(self.st_lbl)
        lc.addWidget(self.trans_card)
        mid_row.addStretch(); mid_row.addLayout(lc)
        mid_row.addSpacerItem(QSpacerItem(40, 0)); self.mic = MicButton(self.mode["color"])
        if parent and hasattr(parent, 'stop_listen_signal'):
            self.mic.clicked.connect(parent.stop_listen_signal.emit)
        mid_row.addWidget(self.mic); mid_row.addSpacerItem(QSpacerItem(40, 0))
        rc = QVBoxLayout(); rc.setSpacing(8)
        for icon in ["🔁", "💡", "⏭"]:
            b = QPushButton(icon)
            b.setFixedSize(44, 44)
            b.setFont(QFont("Segoe UI Emoji", 16))
            b.setStyleSheet(f"background: {C['card']}; border-radius: 22px; color: {C['text2']};")
            rc.addWidget(b)
        mid_row.addLayout(rc); mid_row.addStretch(); vlay.addLayout(mid_row); root.addWidget(vp)

    def add_bubble(self, text: str, is_user: bool, replace_last: bool = False):
        if replace_last and not is_user:
            # Try to find the last Alina bubble
            for i in range(self._chat_lay.count() - 2, -1, -1):
                item = self._chat_lay.itemAt(i)
                if item:
                    w = item.widget()
                    if w and isinstance(w, ChatBubble):
                        if not w.is_user:
                            w.update_text(text)
                            return
        
        b = ChatBubble(text, is_user, self.mode["color"])
        self._chat_lay.insertWidget(self._chat_lay.count() - 1, b)
        
        def scroll_to_bottom():
            sb = self.scroll_area.verticalScrollBar()
            if sb: sb.setValue(sb.maximum())
            
        QTimer.singleShot(100, scroll_to_bottom)

    def clear_chat(self):
        while self._chat_lay.count() > 1:
            item = self._chat_lay.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.deleteLater()

class ProgressScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self); root.setContentsMargins(28, 24, 28, 24); root.setSpacing(16)
        lbl_prog = QLabel("My Progress")
        lbl_prog.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_prog.setStyleSheet(f"color: {C['text']};")
        root.addWidget(lbl_prog)
        
        # Summary row
        srow = QHBoxLayout(); srow.setSpacing(10)
        total = progress_tracker.data["stats"]["total_sessions"]
        avg = sum(progress_tracker.data["stats"]["pronunciation_scores"]) / max(1, len(progress_tracker.data["stats"]["pronunciation_scores"]))
        for val, lbl in [(str(total), "Sessions"), (f"{avg:.0f}%", "Avg Score"), ("7🔥", "Streak")]:
            f = QFrame(); f.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px;")
            cl = QVBoxLayout(f)
            vlbl = QLabel(val)
            vlbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
            vlbl.setStyleSheet(f"color: {C['text']};")
            cl.addWidget(vlbl)
            tlbl = QLabel(lbl)
            tlbl.setFont(QFont("Segoe UI", 10))
            tlbl.setStyleSheet(f"color: {C['text2']};")
            cl.addWidget(tlbl)
            srow.addWidget(f)
        root.addLayout(srow)

        # Words area
        w_panel = QFrame(); w_panel.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px;")
        w_lay = QVBoxLayout(w_panel)
        wl = QLabel("Word tracker")
        wl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        wl.setStyleSheet(f"color: {C['text']};")
        w_lay.addWidget(wl)
        cols = QHBoxLayout()
        for head, words, col in [("Weak", progress_tracker.data["weak_words"][:5], C["coral"]), ("Improved", progress_tracker.data["improved_words"][:5], C["green"])]:
            cv = QVBoxLayout()
            hl = QLabel(head)
            hl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            hl.setStyleSheet(f"color: {col};")
            cv.addWidget(hl)
            for w in words:
                wbl = QLabel(w)
                wbl.setStyleSheet(f"color: {col}; background: {col}22; border-radius: 8px; padding: 4px;")
                cv.addWidget(wbl)
            cv.addStretch(); cols.addLayout(cv)
        w_lay.addLayout(cols); root.addWidget(w_panel); root.addStretch()

# ═══════════════════════════════════════════════════════════════════
#  SETUP WIZARD
# ═══════════════════════════════════════════════════════════════════

class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alina — Initial Setup")
        self.setFixedWidth(500)
        self.setStyleSheet(f"background: {C['bg']}; color: {C['text']};")
        
        lay = QVBoxLayout(self); lay.setContentsMargins(30, 30, 30, 30); lay.setSpacing(15)
        
        logo = QLabel("🚀")
        logo.setFont(QFont("Segoe UI Emoji", 40))
        lay.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("Welcome to Alina")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lay.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        sub = QLabel("To get started, please enter your Groq API key.\nThis is required for voice recognition and AI responses.")
        sub.setFont(QFont("Segoe UI", 10)); sub.setStyleSheet(f"color: {C['text2']};")
        sub.setWordWrap(True); sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        
        # Groq Key
        self.groq_input = QLineEdit()
        self.groq_input.setPlaceholderText("Enter Groq API Key (gsk_...)")
        self.groq_input.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px; padding: 10px; color: {C['text']};")
        lay.addWidget(self.groq_input)
        
        hint = QLabel("You can get a free key at: console.groq.com")
        hint.setFont(QFont("Segoe UI", 9)); hint.setStyleSheet(f"color: {C['text3']};")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        
        lay.addSpacerItem(QSpacerItem(0, 20))
        
        btn = QPushButton("Save & Start")
        btn.setFixedHeight(45); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background: {C['alina']}; color: #0D0A1E; border-radius: 12px; font-weight: bold; }} QPushButton:hover {{ background: #BDB0FC; }}")
        btn.clicked.connect(self.save)
        lay.addWidget(btn)

    def save(self):
        key = self.groq_input.text().strip()
        if not key.startswith("gsk_"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Key", "Please enter a valid Groq API key starting with 'gsk_'.")
            return
        
        from core import config
        config.save_keys({"GROK_API_KEY": key})
        self.accept()

# ═══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════

class AlinaApp(QMainWindow):
    # Signals for thread-safe UI updates
    new_bubble = pyqtSignal(str, bool)
    set_speaking_ui = pyqtSignal(bool)
    set_listening_ui = pyqtSignal(bool)
    update_transcription_ui = pyqtSignal(str)
    stop_listen_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alina — English Voice Coach")
        self.setMinimumSize(1100, 750)
        
        # Logic state
        self.brain = StandaloneBrain()
        self.coach = CoachEngine(self.brain)
        self.coach.transcript_callback = lambda t: self.new_bubble.emit(t, False)
        self.coach.on_speak_callback = lambda b: self.set_speaking_ui.emit(b)
        self.coach.on_listen_callback = lambda b: self.set_listening_ui.emit(b)
        self.coach.on_transcription_callback = lambda t: self.update_transcription_ui.emit(t)
        self.coach.get_rate_callback = lambda: "+0%"
        
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()
        
        self._build_ui()
        self._connect_logic()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.nav = NavBar(); layout.addWidget(self.nav)
        self.stack = QStackedWidget(); layout.addWidget(self.stack, 1)
        self.home = HomeScreen(); self.stack.addWidget(self.home)
        self.progress = ProgressScreen();        self.stack.addWidget(self.progress)
        self.session_screens = {}
        self._active_task = None

    def _connect_logic(self):
        self.nav.mode_selected.connect(self._switch_screen)
        self.home.start_mode.connect(self._start_session)
        self.new_bubble.connect(self._handle_new_bubble)
        self.set_speaking_ui.connect(self._handle_speaking_anim)
        self.set_listening_ui.connect(self._handle_listening_anim)
        self.update_transcription_ui.connect(self._handle_update_transcription)
        self.stop_listen_signal.connect(lambda: self.coach.stop_listen())

    def _switch_screen(self, idx):
        if idx == -1: # Home
            self.stack.setCurrentWidget(self.home)
            self.nav._active = -1
            self.nav._refresh()
            return

        if idx == 7: # Progress (Last item in MODES)
            self.stack.setCurrentWidget(self.progress)
            self.nav._active = 7
            self.nav._refresh()
            return

        # For all other modes (0-6), start a session
        self._start_session(idx)

    def _start_session(self, idx):
        if idx not in self.session_screens:
            s = SessionScreen(idx, parent=self)
            s.back_clicked.connect(lambda: self._stop_session(0))
            self.session_screens[idx] = s; self.stack.addWidget(s)
        self.cur_sess = self.session_screens[idx]
        self.stack.setCurrentWidget(self.cur_sess)
        self.nav._active = idx
        self.nav._refresh()
        mode_key = MODES[idx]["key"]
        
        # Clear UI for the fresh session
        self.cur_sess.clear_chat()
        self.cur_sess.st_lbl.setText("Ready")

        # Schedule safe start in the event loop thread
        asyncio.run_coroutine_threadsafe(self._safe_start_coach(mode_key), self.loop)

    async def _safe_start_coach(self, mode):
        # Cancel any existing tasks in the loop
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task() and task.get_name().startswith("CoachEngine"):
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass

        # Mark this task so we can find it later
        task = asyncio.current_task()
        if task:
            task.set_name(f"CoachEngine.start.{mode}")
        
        # Now start the coach engine
        await self.coach.start(mode=mode)

    def _stop_session(self, target_idx):
        asyncio.run_coroutine_threadsafe(self.coach.stop(), self.loop)
        self._switch_screen(target_idx)

    def _handle_new_bubble(self, text, is_user):
        # Logic to decide if we should replace or add
        replace = False
        if not is_user:
            # If it looks like a timer or live update, replace
            if "⏱️" in text or "Live Transcript" in text or "Live:" in text:
                replace = True
        
        if hasattr(self, 'cur_sess'): 
            self.cur_sess.add_bubble(text, is_user, replace_last=replace)

    def _handle_speaking_anim(self, on):
        if hasattr(self, 'cur_sess'):
            self.cur_sess.avatar.set_speaking(on)
            self.cur_sess.st_lbl.setText("Alina is speaking..." if on else "Ready")
            if on:
                # Finalize any previous user bubble if it was still active
                self.cur_sess.cur_user_bubble = None
                self.cur_sess.trans_card.hide()

    def _handle_listening_anim(self, on):
        if hasattr(self, 'cur_sess'):
            self.cur_sess.mic.set_listening(on)
            self.cur_sess.wave.set_active(on)
            self.cur_sess.st_lbl.setText("Listening..." if on else "Processing...")
            if on: 
                # Create a live-updating user bubble ONLY if one doesn't exist
                if not hasattr(self.cur_sess, 'cur_user_bubble') or self.cur_sess.cur_user_bubble is None:
                    self.cur_sess.cur_user_bubble = ChatBubble("...", True, self.cur_sess.mode["color"])
                    self.cur_sess._chat_lay.insertWidget(self.cur_sess._chat_lay.count() - 1, self.cur_sess.cur_user_bubble)
                
                self.cur_sess.trans_hdr.setText("🎙 Listening...")
                self.cur_sess.trans_card.show()
            else:
                # Keep trans_card visible as "Processing..." or hide? 
                # User wants "just listening show ho".
                if self.cur_sess.st_lbl.text() == "Processing...":
                    self.cur_sess.trans_hdr.setText("⚙️ Processing...")
                else:
                    self.cur_sess.trans_card.hide()

    def _handle_update_transcription(self, text):
        if hasattr(self, 'cur_sess') and text:
            # Update the bubble in the chat history live
            if self.cur_sess.cur_user_bubble:
                self.cur_sess.cur_user_bubble.update_text(text)

def main():
    app = QApplication(sys.argv)
    
    # Check for keys
    from core import config
    if not config.GROK_API_KEY:
        setup = SetupDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
            
    window = AlinaApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
