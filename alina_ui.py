"""
╔══════════════════════════════════════════════════════════════════╗
║   ALINA — AI English Voice Coach                                 ║
║   Beautiful PyQt6 Desktop UI                                     ║
║                                                                  ║
║   pip install PyQt6 groq faster-whisper edge-tts sounddevice    ║
║                    numpy scipy                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, math, random, time
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
    QGraphicsOpacityEffect,
    QSizePolicy,
    QTextEdit,
    QLineEdit,
    QGridLayout,
    QSpacerItem,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    pyqtSignal,
    QThread,
    QPointF,
    QRectF,
    QSize,
    QRect,
    pyqtProperty,
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
    QFontDatabase,
    QPixmap,
    QIcon,
    QPaintEvent,
)

# ═══════════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════

C = {
    "bg": "#080B12",
    "bg2": "#0E1220",
    "bg3": "#141826",
    "card": "#161C2E",
    "card2": "#1C2338",
    "border": "#252D45",
    "border2": "#2E3855",
    "alina": "#A78BFA",  # Alina purple
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
        "key": "casual",
        "icon": "💬",
        "label": "Casual Chat",
        "sub": "Normal gupshup. Short, natural, friendly replies.",
        "color": C["amber"],
        "dim": C["amber_dim"],
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
#  ANIMATED WAVEFORM WIDGET
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

    def _tick(self):
        if self.active:
            for i in range(self.bars):
                self.target[i] = random.uniform(0.08, 1.0)
        for i in range(self.bars):
            self.heights[i] += (self.target[i] - self.heights[i]) * 0.25
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
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


# ═══════════════════════════════════════════════════════════════════
#  ANIMATED MIC BUTTON
# ═══════════════════════════════════════════════════════════════════


class MicButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.listening = False
        self.ring_r = 0.0
        self.ring_a = 0
        self.hover = False
        self.press = False
        self.setFixedSize(120, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._ring_timer = QTimer(self)
        self._ring_timer.timeout.connect(self._ring_tick)

    def set_listening(self, on: bool):
        self.listening = on
        if on:
            self._ring_timer.start(30)
        else:
            self._ring_timer.stop()
            self.ring_r = 0.0
        self.update()

    def _ring_tick(self):
        self.ring_r = (self.ring_r + 1.2) % 60
        self.ring_a = max(0, int(200 * (1 - self.ring_r / 60)))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        base_r = 46

        # outer glow ring (animated)
        if self.listening and self.ring_r > 0:
            rc = QColor(self.color)
            rc.setAlpha(self.ring_a)
            p.setPen(QPen(rc, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            rr = base_r + self.ring_r
            p.drawEllipse(QRectF(cx - rr, cy - rr, rr * 2, rr * 2))

        # static glow
        if self.listening or self.hover:
            for i, a in enumerate([15, 30]):
                gc = QColor(self.color)
                gc.setAlpha(a)
                p.setBrush(gc)
                p.setPen(Qt.PenStyle.NoPen)
                gr = base_r + (2 - i) * 8
                p.drawEllipse(QRectF(cx - gr, cy - gr, gr * 2, gr * 2))

        # main circle
        r = base_r - (4 if self.press else 0)
        grad = QRadialGradient(cx - 8, cy - 8, r * 1.4)
        c1 = QColor(self.color).lighter(130)
        c2 = QColor(self.color)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # mic icon
        p.setPen(
            QPen(QColor("#FFFFFF"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        p.setBrush(Qt.BrushStyle.NoBrush)

        mw, mh = 13, 20
        mr, mbr = 6, 4
        mx, my = cx - mw / 2, cy - mh / 2 - 3

        path = QPainterPath()
        path.addRoundedRect(QRectF(mx, my, mw, mh), mr, mr)
        p.drawPath(path)

        # stand
        p.drawArc(QRectF(cx - 11, cy + 3, 22, 14), 0, -180 * 16)
        p.drawLine(int(cx), int(cy + 16), int(cx), int(cy + 21))
        p.drawLine(int(cx - 6), int(cy + 21), int(cx + 6), int(cy + 21))
        p.end()

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mousePressEvent(self, e):
        self.press = True
        self.update()

    def mouseReleaseEvent(self, e):
        self.press = False
        if self.rect().contains(e.pos()):
            self.clicked.emit()
        self.update()


# ═══════════════════════════════════════════════════════════════════
#  ALINA AVATAR (animated lips)
# ═══════════════════════════════════════════════════════════════════


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

        self._blink_pause = QTimer(self)
        self._blink_pause.setSingleShot(True)
        self._blink_pause.timeout.connect(self._start_blink)
        self._schedule_blink()

    def set_speaking(self, on: bool):
        self.speaking = on
        if on:
            self._talk_t.start(60)
        else:
            self._talk_t.stop()
            self.mouth_open = 0.0
            self.update()

    def _talk_tick(self):
        self.mouth_open = abs(math.sin(time.time() * 8)) * 0.9
        self.update()

    def _schedule_blink(self):
        self._blink_pause.start(random.randint(2000, 5000))

    def _start_blink(self):
        self._blink_dir = -1

    def _blink_tick(self):
        if self._blink_dir == -1:
            self.blink = max(0.0, self.blink - 0.25)
            if self.blink == 0.0:
                self._blink_dir = 1
        elif self._blink_dir == 1:
            self.blink = min(1.0, self.blink + 0.25)
            if self.blink == 1.0:
                self._blink_dir = 0
                self._schedule_blink()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = 45, 45
        r = 38

        # outer ring glow
        if self.speaking:
            for i, a in enumerate([20, 40]):
                gc = QColor("#A78BFA")
                gc.setAlpha(a)
                p.setBrush(gc)
                p.setPen(Qt.PenStyle.NoPen)
                gr = r + (2 - i) * 5
                p.drawEllipse(QRectF(cx - gr, cy - gr, gr * 2, gr * 2))

        # face bg
        grad = QRadialGradient(cx - 5, cy - 8, r)
        grad.setColorAt(0, QColor("#2A1F4E"))
        grad.setColorAt(1, QColor("#13102A"))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor("#A78BFA"), 1.5))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # eyes
        ey = cy - 8
        for ex in [cx - 11, cx + 11]:
            eye_h = max(1, int(9 * self.blink))
            eye_y = ey - eye_h // 2
            p.setBrush(QColor("#E2E8F8"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRect(int(ex) - 5, eye_y, 10, eye_h))
            # pupil
            if self.blink > 0.3:
                p.setBrush(QColor("#7C3AED"))
                py2 = ey - int(3 * self.blink)
                p.drawEllipse(QRect(int(ex) - 2, py2 - 2, 5, int(5 * self.blink)))

        # mouth
        mo = self.mouth_open
        mouth_w = 18
        mouth_x = cx - mouth_w // 2
        mouth_y = cy + 10
        p.setBrush(QColor("#1A0A2E") if mo > 0.1 else Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#E2E8F8"), 1.5))
        mouth_h = max(2, int(mo * 10))
        p.drawRoundedRect(
            QRect(mouth_x, mouth_y - mouth_h // 2, mouth_w, max(4, mouth_h)), 4, 4
        )

        # hair accent
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#A78BFA"), 2.5))
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2 * 0.7), 30 * 16, 120 * 16)
        p.end()


# ═══════════════════════════════════════════════════════════════════
#  CHAT BUBBLE
# ═══════════════════════════════════════════════════════════════════


class ChatBubble(QFrame):
    def __init__(self, text: str, is_user: bool, accent: str, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.accent = accent
        self._setup(text)

    def _setup(self, text):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        who = QLabel("You" if self.is_user else "Alina")
        who.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        who.setStyleSheet(f"color: {'#94A3C4' if self.is_user else self.accent};")
        lay.addWidget(who)

        self.body = QLabel(text)
        self.body.setWordWrap(True)
        self.body.setFont(QFont("Segoe UI", 11))
        self.body.setStyleSheet(f"color: {C['text']}; line-height: 160%;")
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.body)

        if self.is_user:
            bg = "#1A2545"
            border = f"border-left: 2px solid #2E3855;"
        else:
            bg = "#1A1630"
            border = f"border-left: 3px solid {self.accent};"

        self.setStyleSheet(
            f"""
            QFrame {{
                background: {bg};
                {border}
                border-radius: 12px;
            }}
        """
        )

    def append(self, chunk: str):
        self.body.setText(self.body.text() + chunk)

    def add_correction(self, text: str):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {self.accent}44;")
        self.layout().addWidget(sep)

        c = QLabel(f"✏  {text}")
        c.setWordWrap(True)
        c.setFont(QFont("Segoe UI", 10))
        c.setStyleSheet(
            f"""
            color: {C['amber']};
            background: {C['amber_dim']};
            border-radius: 6px;
            padding: 6px 10px;
        """
        )
        self.layout().addWidget(c)


# ═══════════════════════════════════════════════════════════════════
#  NAV SIDEBAR
# ═══════════════════════════════════════════════════════════════════


class NavBar(QWidget):
    mode_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(72)
        self._active = 0
        self._btns = []
        self._setup()

    def _setup(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 16, 8, 16)
        lay.setSpacing(4)

        # Logo
        logo = QLabel("A")
        logo.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"color: {C['alina']}; margin-bottom: 16px;")
        lay.addWidget(logo)

        for i, m in enumerate(MODES):
            btn = QPushButton(m["icon"])
            btn.setFixedSize(50, 50)
            btn.setFont(QFont("Segoe UI Emoji", 18))
            btn.setToolTip(m["label"])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select(idx))
            self._btns.append(btn)
            lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        lay.addStretch()

        # Settings icon
        sett = QPushButton("⚙")
        sett.setFixedSize(50, 50)
        sett.setFont(QFont("Segoe UI Emoji", 16))
        sett.setCursor(Qt.CursorShape.PointingHandCursor)
        sett.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; border: none;
                color: {C['text3']};
            }}
            QPushButton:hover {{ color: {C['text2']}; }}
        """
        )
        lay.addWidget(sett, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setStyleSheet(
            f"""
            QWidget {{
                background: {C['bg2']};
                border-right: 1px solid {C['border']};
            }}
        """
        )
        self._refresh()

    def _select(self, idx: int):
        self._active = idx
        self._refresh()
        self.mode_selected.emit(idx)

    def _refresh(self):
        for i, btn in enumerate(self._btns):
            m = MODES[i]
            if i == self._active:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: {m['dim']};
                        border: 1px solid {m['color']}55;
                        border-radius: 14px;
                        color: {m['color']};
                    }}
                """
                )
            else:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background: transparent;
                        border: 1px solid transparent;
                        border-radius: 14px;
                        color: {C['text3']};
                    }}
                    QPushButton:hover {{
                        background: {m['dim']};
                        color: {m['color']};
                        border: 1px solid {m['color']}33;
                    }}
                """
                )


# ═══════════════════════════════════════════════════════════════════
#  HOME SCREEN
# ═══════════════════════════════════════════════════════════════════


class HomeScreen(QWidget):
    start_mode = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C['bg']};")
        self._setup()

    def _setup(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # ── Top bar ──
        top = QHBoxLayout()
        av = AlinaAvatar()
        top.addWidget(av)

        intro = QVBoxLayout()
        intro.setSpacing(2)
        name_lbl = QLabel("Hi, I'm Alina 👋")
        name_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {C['text']};")
        sub_lbl = QLabel("Your personal English voice coach. Let's practice!")
        sub_lbl.setFont(QFont("Segoe UI", 11))
        sub_lbl.setStyleSheet(f"color: {C['text2']};")
        intro.addWidget(name_lbl)
        intro.addWidget(sub_lbl)
        top.addLayout(intro)
        top.addStretch()

        streak = self._pill("🔥  Day 7 streak")
        hrs = self._pill("⏱  4.5 hrs total")
        top.addWidget(streak)
        top.addWidget(hrs)
        root.addLayout(top)

        # divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['border']};")
        root.addWidget(div)

        # ── Daily routine card ──
        daily = self._daily_card()
        root.addWidget(daily)

        # ── Mode grid ──
        grid_lbl = QLabel("Practice modes")
        grid_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        grid_lbl.setStyleSheet(f"color: {C['text3']}; letter-spacing: 2px;")
        root.addWidget(grid_lbl)

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, m in enumerate(MODES[1:], 1):
            card = self._mode_card(i, m)
            grid.addWidget(card, (i - 1) // 3, (i - 1) % 3)
        root.addLayout(grid)
        root.addStretch()

    def _pill(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setFont(QFont("Segoe UI", 10))
        l.setStyleSheet(
            f"""
            color: {C['text2']};
            background: {C['card']};
            border: 1px solid {C['border']};
            border-radius: 16px;
            padding: 5px 14px;
        """
        )
        return l

    def _daily_card(self) -> QFrame:
        f = QFrame()
        f.setCursor(Qt.CursorShape.PointingHandCursor)
        f.setStyleSheet(
            f"""
            QFrame {{
                background: {C['card']};
                border: 1px solid {C['alina']}55;
                border-radius: 16px;
            }}
            QFrame:hover {{
                background: {C['card2']};
                border: 1px solid {C['alina']}99;
            }}
        """
        )
        lay = QHBoxLayout(f)
        lay.setContentsMargins(20, 16, 20, 16)

        icon = QLabel("📅")
        icon.setFont(QFont("Segoe UI Emoji", 28))
        lay.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(4)
        t = QLabel("Today's Daily Routine")
        t.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        t.setStyleSheet(f"color: {C['text']};")
        s = QLabel("4 steps · ~20 min · 2 of 4 completed")
        s.setFont(QFont("Segoe UI", 10))
        s.setStyleSheet(f"color: {C['text2']};")

        steps_row = QHBoxLayout()
        steps_row.setSpacing(6)
        for label, done in [
            ("Warm-up", True),
            ("Speaking", True),
            ("Pronunciation", False),
            ("Interview", False),
        ]:
            pill = QLabel(("✓ " if done else "") + label)
            pill.setFont(QFont("Segoe UI", 9))
            pill.setStyleSheet(
                f"""
                color: {C['green'] if done else C['text3']};
                background: {C['green_dim'] if done else C['card2']};
                border: 1px solid {C['green'] + '55' if done else C['border']};
                border-radius: 10px;
                padding: 2px 10px;
            """
            )
            steps_row.addWidget(pill)
        steps_row.addStretch()

        info.addWidget(t)
        info.addWidget(s)
        info.addLayout(steps_row)
        lay.addLayout(info)
        lay.addStretch()

        go = QPushButton("Continue →")
        go.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        go.setCursor(Qt.CursorShape.PointingHandCursor)
        go.setStyleSheet(
            f"""
            QPushButton {{
                background: {C['alina']};
                color: #0D0A1E;
                border: none;
                border-radius: 10px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{ background: #BDB0FC; }}
        """
        )
        go.clicked.connect(lambda: self.start_mode.emit(0))
        lay.addWidget(go)
        return f

    def _mode_card(self, idx: int, m: dict) -> QFrame:
        f = QFrame()
        f.setCursor(Qt.CursorShape.PointingHandCursor)
        f.setMinimumHeight(110)
        f.setStyleSheet(
            f"""
            QFrame {{
                background: {C['card']};
                border: 1px solid {C['border']};
                border-radius: 14px;
            }}
            QFrame:hover {{
                background: {m['dim']};
                border: 1px solid {m['color']}66;
            }}
        """
        )
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        ic = QLabel(m["icon"])
        ic.setFont(QFont("Segoe UI Emoji", 22))
        lbl = QLabel(m["label"])
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color: {C['text']};")
        sub = QLabel(m["sub"])
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet(f"color: {C['text2']};")
        sub.setWordWrap(True)

        lay.addWidget(ic)
        lay.addWidget(lbl)
        lay.addWidget(sub)
        lay.addStretch()

        # bottom accent line
        bar = QFrame()
        bar.setFixedHeight(2)
        bar.setStyleSheet(f"background: {m['color']}; border-radius: 1px;")
        lay.addWidget(bar)

        f.mousePressEvent = lambda e, i=idx: self.start_mode.emit(i)
        return f


# ═══════════════════════════════════════════════════════════════════
#  SESSION SCREEN  (voice chat)
# ═══════════════════════════════════════════════════════════════════


class SessionScreen(QWidget):
    back_clicked = pyqtSignal()

    def __init__(self, mode_idx: int = 1, parent=None):
        super().__init__(parent)
        self.mode = MODES[mode_idx]
        self.listening = False
        self.speaking = False
        self.setStyleSheet(f"background: {C['bg']};")
        self._setup()

    def _setup(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        hdr = QFrame()
        hdr.setFixedHeight(60)
        hdr.setStyleSheet(
            f"""
            background: {C['bg2']};
            border-bottom: 1px solid {C['border']};
        """
        )
        hlay = QHBoxLayout(hdr)
        hlay.setContentsMargins(16, 0, 16, 0)

        back = QPushButton("← Back")
        back.setFont(QFont("Segoe UI", 10))
        back.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; border: none;
                color: {C['text2']};
            }}
            QPushButton:hover {{ color: {C['text']}; }}
        """
        )
        back.clicked.connect(self.back_clicked.emit)
        hlay.addWidget(back)

        self.live_dot = QLabel("●")
        self.live_dot.setStyleSheet(f"color: {C['coral']}; font-size: 10px;")
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(
            lambda: self.live_dot.setVisible(not self.live_dot.isVisible())
        )
        self._dot_timer.start(600)

        mode_lbl = QLabel(f"  {self.mode['icon']}  {self.mode['label']}")
        mode_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        mode_lbl.setStyleSheet(f"color: {C['text']};")
        hlay.addWidget(self.live_dot)
        hlay.addWidget(mode_lbl)
        hlay.addStretch()

        self.timer_lbl = QLabel("00:00")
        self.timer_lbl.setFont(QFont("Consolas", 11))
        self.timer_lbl.setStyleSheet(f"color: {C['text2']};")
        hlay.addWidget(self.timer_lbl)
        self._elapsed = 0
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start(1000)

        root.addWidget(hdr)

        # ── Chat area ──
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            f"""
            QScrollArea {{ border: none; background: {C['bg']}; }}
            QScrollBar:vertical {{
                background: {C['bg2']}; width: 4px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border2']}; border-radius: 2px;
            }}
        """
        )
        self._chat_w = QWidget()
        self._chat_w.setStyleSheet(f"background: {C['bg']};")
        self._chat_lay = QVBoxLayout(self._chat_w)
        self._chat_lay.setContentsMargins(20, 16, 20, 16)
        self._chat_lay.setSpacing(14)
        self._chat_lay.addStretch()
        self.scroll.setWidget(self._chat_w)
        root.addWidget(self.scroll, 1)

        # add welcome bubble
        self._add_ai_bubble(
            f"Hi! I'm Alina 😊  Let's start your {self.mode['label']} session.\n"
            "Press the mic button and start speaking whenever you're ready!"
        )

        # ── Voice panel ──
        vp = QFrame()
        vp.setStyleSheet(
            f"""
            background: {C['bg2']};
            border-top: 1px solid {C['border']};
        """
        )
        vlay = QVBoxLayout(vp)
        vlay.setContentsMargins(20, 14, 20, 14)
        vlay.setSpacing(12)

        # waveform
        self.wave = WaveformWidget(self.mode["color"])
        vlay.addWidget(self.wave)

        # avatar + mic row
        mid_row = QHBoxLayout()
        mid_row.setSpacing(0)

        # left: avatar + status
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        left_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar = AlinaAvatar()
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setFont(QFont("Segoe UI", 10))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(f"color: {C['text2']};")
        left_col.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        left_col.addWidget(self.status_lbl)

        # center: mic
        center_col = QVBoxLayout()
        center_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mic = MicButton(self.mode["color"])
        self.mic.clicked.connect(self._toggle_mic)
        self.mic_hint = QLabel("Tap to speak")
        self.mic_hint.setFont(QFont("Segoe UI", 10))
        self.mic_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mic_hint.setStyleSheet(f"color: {C['text3']};")
        center_col.addWidget(self.mic, alignment=Qt.AlignmentFlag.AlignCenter)
        center_col.addWidget(self.mic_hint)

        # right: controls
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for icon, tip in [("🔁", "Replay"), ("💡", "Explain again"), ("⏭", "Skip")]:
            b = QPushButton(icon)
            b.setFixedSize(44, 44)
            b.setFont(QFont("Segoe UI Emoji", 16))
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"""
                QPushButton {{
                    background: {C['card']};
                    border: 1px solid {C['border']};
                    border-radius: 22px;
                    color: {C['text2']};
                }}
                QPushButton:hover {{
                    background: {C['card2']};
                    border: 1px solid {C['border2']};
                }}
            """
            )
            right_col.addWidget(b, alignment=Qt.AlignmentFlag.AlignCenter)

        mid_row.addStretch()
        mid_row.addLayout(left_col)
        mid_row.addSpacerItem(QSpacerItem(40, 0))
        mid_row.addLayout(center_col)
        mid_row.addSpacerItem(QSpacerItem(40, 0))
        mid_row.addLayout(right_col)
        mid_row.addStretch()
        vlay.addLayout(mid_row)

        # speed slider
        spd_row = QHBoxLayout()
        spd_lbl = QLabel("Alina's speed:")
        spd_lbl.setFont(QFont("Segoe UI", 10))
        spd_lbl.setStyleSheet(f"color: {C['text2']};")
        self.spd_slider = QSlider(Qt.Orientation.Horizontal)
        self.spd_slider.setRange(1, 5)
        self.spd_slider.setValue(3)
        self.spd_slider.setFixedWidth(140)
        self.spd_slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {C['border2']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 16px; height: 16px;
                margin: -6px 0;
                background: {self.mode['color']};
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.mode['color']};
                border-radius: 2px;
            }}
        """
        )
        self.spd_val = QLabel("Normal")
        self.spd_val.setFont(QFont("Segoe UI", 10))
        self.spd_val.setStyleSheet(f"color: {C['text2']}; min-width: 60px;")
        self.spd_slider.valueChanged.connect(self._spd_changed)
        spd_row.addStretch()
        spd_row.addWidget(spd_lbl)
        spd_row.addSpacerItem(QSpacerItem(10, 0))
        spd_row.addWidget(self.spd_slider)
        spd_row.addSpacerItem(QSpacerItem(8, 0))
        spd_row.addWidget(self.spd_val)
        spd_row.addStretch()
        vlay.addLayout(spd_row)

        root.addWidget(vp)

    def _tick_clock(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_lbl.setText(f"{m:02d}:{s:02d}")

    def _toggle_mic(self):
        self.listening = not self.listening
        self.mic.set_listening(self.listening)
        self.wave.set_active(self.listening)
        if self.listening:
            self.status_lbl.setText("Listening...")
            self.mic_hint.setText("Tap to stop")
            self._add_user_bubble("🎙  Listening...")
        else:
            self.status_lbl.setText("Alina is thinking...")
            self.mic_hint.setText("Tap to speak")
            self.avatar.set_speaking(True)
            self.wave.set_active(True)
            QTimer.singleShot(2000, self._simulate_response)

    def _simulate_response(self):
        self.avatar.set_speaking(False)
        self.wave.set_active(False)
        self.status_lbl.setText("Ready")
        self._add_ai_bubble(
            "Great effort! Your sentence structure was clear. "
            'One small fix: say "I have been working" instead of "I am working" '
            "when describing ongoing experience. Try it again!"
        )

    def _add_user_bubble(self, text: str):
        b = ChatBubble(text, True, self.mode["color"])
        idx = self._chat_lay.count() - 1
        self._chat_lay.insertWidget(idx, b)
        QTimer.singleShot(
            50,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            ),
        )

    def _add_ai_bubble(self, text: str):
        b = ChatBubble(text, False, self.mode["color"])
        idx = self._chat_lay.count() - 1
        self._chat_lay.insertWidget(idx, b)
        QTimer.singleShot(
            50,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            ),
        )

    def _spd_changed(self, v: int):
        labels = {1: "Very slow", 2: "Slow", 3: "Normal", 4: "Fast", 5: "Very fast"}
        self.spd_val.setText(labels[v])


# ═══════════════════════════════════════════════════════════════════
#  PROGRESS SCREEN
# ═══════════════════════════════════════════════════════════════════


class SkillBar(QWidget):
    def __init__(self, label: str, pct: int, change: str, color: str, parent=None):
        super().__init__(parent)
        self._pct = 0
        self._target = pct
        self._color = QColor(color)
        self._setup(label, pct, change)

        self._anim_t = QTimer(self)
        self._anim_t.timeout.connect(self._step)

    def show_anim(self):
        self._anim_t.start(20)

    def _step(self):
        if self._pct < self._target:
            self._pct = min(self._target, self._pct + 2)
            self.update()
        else:
            self._anim_t.stop()

    def _setup(self, label, pct, change):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        row = QHBoxLayout()
        l = QLabel(label)
        l.setFont(QFont("Segoe UI", 11))
        l.setStyleSheet(f"color: {C['text']};")
        r = QLabel(f"{pct}%  {change}")
        r.setFont(QFont("Segoe UI", 10))
        r.setStyleSheet(f"color: {C['green']};")
        row.addWidget(l)
        row.addStretch()
        row.addWidget(r)
        lay.addLayout(row)
        lay.addWidget(self)

    def paintEvent(self, e):
        if self.height() < 8:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = 7
        y = self.height() - h

        # track
        p.setBrush(QColor(C["card2"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, y, self.width(), h), 3, 3)

        # fill
        fw = max(0, int(self.width() * self._pct / 100))
        grad = QLinearGradient(0, 0, fw, 0)
        grad.setColorAt(0, self._color.lighter(140))
        grad.setColorAt(1, self._color)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(0, y, fw, h), 3, 3)
        p.end()

    def sizeHint(self):
        return QSize(200, 36)


class ProgressScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C['bg']};")
        self._setup()

    def _setup(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{ border: none; background: {C['bg']}; }}
            QScrollBar:vertical {{
                background: {C['bg2']}; width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border2']}; border-radius: 2px;
            }}
        """
        )
        container = QWidget()
        container.setStyleSheet(f"background: {C['bg']};")
        root = QVBoxLayout(container)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # title
        t = QLabel("My Progress")
        t.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {C['text']};")
        root.addWidget(t)

        # stat cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        for val, lbl, ch in [
            ("23", "Sessions", ""),
            ("4.5h", "Practice time", "+1.2h"),
            ("72", "Avg score", "↑+8"),
            ("7🔥", "Streak", ""),
        ]:
            card = QFrame()
            card.setStyleSheet(
                f"""
                background: {C['card']}; border: 1px solid {C['border']};
                border-radius: 14px;
            """
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            vl = QLabel(val)
            vl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
            vl.setStyleSheet(f"color: {C['text']};")
            ll = QLabel(lbl)
            ll.setFont(QFont("Segoe UI", 10))
            ll.setStyleSheet(f"color: {C['text2']};")
            cl.addWidget(vl)
            cl.addWidget(ll)
            if ch:
                chg = QLabel(ch)
                chg.setFont(QFont("Segoe UI", 10))
                chg.setStyleSheet(f"color: {C['green']};")
                cl.addWidget(chg)
            stats_row.addWidget(card)
        root.addLayout(stats_row)

        # skills + word tracker row
        two_col = QHBoxLayout()
        two_col.setSpacing(12)

        # skills panel
        sk_panel = QFrame()
        sk_panel.setStyleSheet(
            f"""
            background: {C['card']}; border: 1px solid {C['border']};
            border-radius: 14px;
        """
        )
        sk_lay = QVBoxLayout(sk_panel)
        sk_lay.setContentsMargins(18, 16, 18, 16)
        sk_lay.setSpacing(10)
        sk_title = QLabel("Skill breakdown")
        sk_title.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        sk_title.setStyleSheet(f"color: {C['text']};")
        sk_lay.addWidget(sk_title)
        self._skill_bars = []
        for lbl, pct, ch, col in [
            ("Vocabulary", 88, "↑+8", C["alina"]),
            ("Grammar", 78, "↑+12", C["teal"]),
            ("Fluency", 70, "→", C["blue"]),
            ("Pronunciation", 61, "↑+5", C["amber"]),
        ]:
            sb = SkillBar(lbl, pct, ch, col)
            sk_lay.addWidget(sb)
            self._skill_bars.append(sb)
        two_col.addWidget(sk_panel, 3)

        # word tracker
        wt_panel = QFrame()
        wt_panel.setStyleSheet(
            f"""
            background: {C['card']}; border: 1px solid {C['border']};
            border-radius: 14px;
        """
        )
        wt_lay = QVBoxLayout(wt_panel)
        wt_lay.setContentsMargins(18, 16, 18, 16)
        wt_lay.setSpacing(8)
        wt_title = QLabel("Word tracker")
        wt_title.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        wt_title.setStyleSheet(f"color: {C['text']};")
        wt_lay.addWidget(wt_title)

        cols = QHBoxLayout()
        cols.setSpacing(8)
        for col_title, words, bg, fg in [
            (
                "Weak",
                ["Particularly", "Comfortable", "Responsibility"],
                C["coral_dim"],
                C["coral"],
            ),
            (
                "Improving",
                ["Entrepreneur", "Specifically", "Alternatively"],
                C["amber_dim"],
                C["amber"],
            ),
            (
                "Mastered",
                ["Professional", "Experience", "Communication"],
                C["green_dim"],
                C["green"],
            ),
        ]:
            cv = QVBoxLayout()
            cv.setSpacing(4)
            hd = QLabel(col_title)
            hd.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            hd.setStyleSheet(f"color: {fg}; letter-spacing: 1px;")
            cv.addWidget(hd)
            for w in words:
                wl = QLabel(w)
                wl.setFont(QFont("Segoe UI", 10))
                wl.setStyleSheet(
                    f"""
                    color: {fg}; background: {bg};
                    border-radius: 10px; padding: 3px 10px;
                """
                )
                cv.addWidget(wl)
            cv.addStretch()
            cols.addLayout(cv)
        wt_lay.addLayout(cols)
        two_col.addWidget(wt_panel, 2)
        root.addLayout(two_col)

        # Diagnostic report
        rpt = QFrame()
        rpt.setStyleSheet(
            f"""
            background: {C['card']}; border: 1px solid {C['border']};
            border-radius: 14px;
        """
        )
        rl = QVBoxLayout(rpt)
        rl.setContentsMargins(20, 18, 20, 18)
        rl.setSpacing(12)

        rh = QHBoxLayout()
        rt = QLabel("Alina's Diagnostic Report — Week 1")
        rt.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        rt.setStyleSheet(f"color: {C['text']};")
        rd = QLabel("Apr 1–8, 2026")
        rd.setFont(QFont("Segoe UI", 10))
        rd.setStyleSheet(f"color: {C['text2']};")
        rh.addWidget(rt)
        rh.addStretch()
        rh.addWidget(rd)
        rl.addLayout(rh)

        ml = QLabel("Top mistakes this week")
        ml.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        ml.setStyleSheet(f"color: {C['text3']}; letter-spacing: 1px;")
        rl.addWidget(ml)

        for n, txt in [
            ("1", "Tense confusion — was / were / have been"),
            ("2", "Missing articles — a / an / the"),
            ("3", "Word stress on 2-syllable words"),
        ]:
            mf = QFrame()
            mf.setStyleSheet(
                f"""
                background: {C['bg3']}; border: 1px solid {C['border']};
                border-radius: 8px;
            """
            )
            mrow = QHBoxLayout(mf)
            mrow.setContentsMargins(12, 8, 12, 8)
            num = QLabel(n)
            num.setFixedSize(24, 24)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            num.setStyleSheet(
                f"""
                color: {C['coral']}; background: {C['coral_dim']};
                border-radius: 12px;
            """
            )
            info = QLabel(txt)
            info.setFont(QFont("Segoe UI", 11))
            info.setStyleSheet(f"color: {C['text']};")
            mrow.addWidget(num)
            mrow.addSpacerItem(QSpacerItem(10, 0))
            mrow.addWidget(info)
            mrow.addStretch()
            rl.addWidget(mf)

        # 5-day plan
        pl = QLabel("Your 5-day improvement plan")
        pl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        pl.setStyleSheet(f"color: {C['text3']}; letter-spacing: 1px;")
        rl.addWidget(pl)

        plan_row = QHBoxLayout()
        plan_row.setSpacing(8)
        days = [
            ("1", "Articles\na/an/the", True, True),
            ("2", "Articles\ndrill", True, True),
            ("3", "Tense\ndrills", True, False),
            ("4", "Pronunciation\nfocus", False, False),
            ("5", "Full mock\ninterview", False, False),
        ]
        for num, task, done, completed in days:
            df = QFrame()
            if done and not completed:
                border = f"2px solid {C['alina']};"
                bg = C["alina_dim"]
            elif completed:
                border = f"1px solid {C['green']}55;"
                bg = C["green_dim"]
            else:
                border = f"1px solid {C['border']};"
                bg = C["card2"]
            df.setStyleSheet(
                f"""
                background: {bg}; border: {border}
                border-radius: 10px;
            """
            )
            df.setMinimumHeight(80)
            dlay = QVBoxLayout(df)
            dlay.setContentsMargins(10, 10, 10, 10)
            dn = QLabel(f"Day {num}" + (" ✓" if completed else ""))
            dn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            dn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col = C["green"] if completed else (C["alina"] if done else C["text2"])
            dn.setStyleSheet(f"color: {col};")
            dt = QLabel(task)
            dt.setFont(QFont("Segoe UI", 9))
            dt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dt.setStyleSheet(f"color: {col};")
            dlay.addWidget(dn)
            dlay.addWidget(dt)
            plan_row.addWidget(df)
        rl.addLayout(plan_row)

        # CTA buttons
        btn_row = QHBoxLayout()
        start_btn = QPushButton("▶  Start Today's Plan")
        start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {C['alina']}; color: #0D0A1E;
                border: none; border-radius: 10px; padding: 10px 24px;
            }}
            QPushButton:hover {{ background: #BDB0FC; }}
        """
        )
        pdf_btn = QPushButton("⬇  Save PDF")
        pdf_btn.setFont(QFont("Segoe UI", 11))
        pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pdf_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; color: {C['text2']};
                border: 1px solid {C['border2']}; border-radius: 10px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{ color: {C['text']}; border-color: {C['text3']}; }}
        """
        )
        btn_row.addWidget(start_btn)
        btn_row.addWidget(pdf_btn)
        btn_row.addStretch()
        rl.addLayout(btn_row)

        root.addWidget(rpt)
        root.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        QTimer.singleShot(400, lambda: [sb.show_anim() for sb in self._skill_bars])


# ═══════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alina — English Voice Coach")
        self.setMinimumSize(1000, 680)
        self.resize(1100, 740)
        self._apply_palette()
        self._build()

    def _apply_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
        pal.setColor(QPalette.ColorRole.Base, QColor(C["bg2"]))
        pal.setColor(QPalette.ColorRole.Text, QColor(C["text"]))
        self.setPalette(pal)

    def _build(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        h = QHBoxLayout(root_w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.nav = NavBar()
        self.nav.mode_selected.connect(self._switch)
        h.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {C['bg']};")

        self.home_screen = HomeScreen()
        self.home_screen.start_mode.connect(self._switch)
        self.stack.addWidget(self.home_screen)

        self._session_cache = {}

        self.progress_screen = ProgressScreen()

        h.addWidget(self.stack, 1)

    def _switch(self, idx: int):
        if idx == 5:  # progress
            if self.stack.indexOf(self.progress_screen) == -1:
                self.stack.addWidget(self.progress_screen)
            self.stack.setCurrentWidget(self.progress_screen)
            return

        if idx == 0:  # home
            self.stack.setCurrentWidget(self.home_screen)
            return

        # session screens
        if idx not in self._session_cache:
            s = SessionScreen(idx)
            s.back_clicked.connect(lambda: self._switch(0))
            self._session_cache[idx] = s
            self.stack.addWidget(s)

        self.stack.setCurrentWidget(self._session_cache[idx])


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════


def main():
    # PyQt6 handles High-DPI automatically — no manual setAttribute needed
    app = QApplication(sys.argv)
    app.setApplicationName("Alina")
    app.setApplicationDisplayName("Alina — English Voice Coach")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
