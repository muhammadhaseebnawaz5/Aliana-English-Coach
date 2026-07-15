# 🎙️ Alina English Coach

<div align="center">

**An AI-powered desktop application to help you master American English — speaking, pronunciation, and professional communication.**

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-purple?style=for-the-badge)
![AI Powered](https://img.shields.io/badge/AI-Groq%20%7C%20OpenRouter%20%7C%20HuggingFace-orange?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightblue?style=for-the-badge&logo=windows)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## 📖 Overview

**Alina English Coach** is a premium, AI-driven desktop coaching application built with PyQt6. It acts as your personal American English tutor — available 24/7 — helping you improve spoken English, ace mock interviews, master pronunciation, and build confidence in professional communication.

Alina uses a multi-provider LLM backend (Groq, OpenRouter, HuggingFace) with automatic fallback so the coaching never stops, even if one API is unavailable.

---

## ✨ Features

| Module | Description |
|---|---|
| 🗣️ **Speaking Practice** | Real-time conversation with AI feedback on fluency and grammar |
| 🎙️ **Pronunciation Drill** | Targeted drills on TH sounds, R sounds, V vs W, T-flap, and more |
| 💼 **Mock Interview** | Simulated job interviews with professional feedback |
| 🎤 **Presentation Rehearsal** | Practice pitches and presentations out loud |
| 🔬 **Practice Lab** | Free-form English exercises and on-the-fly corrections |
| 📊 **Progress Tracker** | Tracks your sessions, mistakes, and improvement over time |

### 🤖 AI Voice & Intelligence
- **Text-to-Speech**: Microsoft Edge TTS with `en-US-JennyNeural` (American female accent)
- **Speech-to-Text**: English-only STT via SoundDevice
- **LLM Fallback Chain**: Tries multiple models in order — Groq → OpenRouter → HuggingFace — for maximum uptime

---

## 🏗️ Project Structure

```
alina-english-coaching/
│
├── app.py                           # Main entry point & PyQt6 UI shell
├── alina_ui.py                      # Extended UI components
├── app_icon.ico                     # Application icon
│
├── core/
│   ├── brain.py                     # LLM client manager & JSON parser
│   └── config.py                    # API keys, model chain, UI colors, coach settings
│
├── english_coach/
│   ├── coach_engine.py              # Main orchestrator: voice I/O, routing, corrections
│   ├── speaking_practice.py         # Speaking practice mode
│   ├── pronunciation_drill.py       # Pronunciation drill sessions
│   ├── mock_interview.py            # Mock job interview simulator
│   ├── presentation_rehearsal.py    # Presentation rehearsal mode
│   ├── practice_lab.py              # Free-form practice lab
│   └── progress_tracker.py         # Session tracking & progress analytics
│
├── data/
│   ├── english_coach_progress.json  # Persistent progress data
│   └── mistakes_log.txt             # Log of corrections and mistakes
│
├── build_app.bat                    # One-click build script (PyInstaller)
├── install_alina.ps1                # Windows installer (shortcuts + registry)
└── uninstall_alina.ps1              # Clean uninstaller
```

---

## ⚙️ Prerequisites

- **Python 3.12** (recommended)
- **Windows OS** (primary platform; macOS/Linux partially supported)
- API keys for at least one LLM provider (see [Configuration](#-configuration))

---

## 🚀 Installation & Setup

### Option 1 — Run from Source (Development)

**1. Clone the repository:**
```bash
git clone https://github.com/muhammadhaseebnawaz5/Aliana-English-Coach.git
cd Aliana-English-Coach
```

**2. Install dependencies:**
```bash
py -3.12 -m pip install PyQt6 openai groq edge_tts sounddevice soundfile pygame pillow pyinstaller
```

**3. Configure your API keys** (see [Configuration](#-configuration) below).

**4. Run the app:**
```bash
py -3.12 app.py
```

---

### Option 2 — Build a Standalone `.exe`

Run the build script from the project root:

```bash
build_app.bat
```

This will:
1. Install all required dependencies automatically
2. Bundle the app into a single `.exe` using PyInstaller
3. Output the executable to the `dist/` folder

---

### Option 3 — Install on Windows (with Shortcuts)

After building the `.exe`, run the installer:

```powershell
powershell -ExecutionPolicy Bypass -File install_alina.ps1
```

This will:
- Copy the app to `%LOCALAPPDATA%\AlinaCoach\`
- Create a **Desktop shortcut**
- Add to **Start Menu**
- Register in **Windows Apps (Add/Remove Programs)**

To uninstall:
```powershell
powershell -ExecutionPolicy Bypass -File uninstall_alina.ps1
```

---

## 🔑 Configuration

API keys are stored in:
```
%LOCALAPPDATA%\AlinaCoach\data\api_keys.json
```

Create this file with the following structure:

```json
{
    "GROK_API_KEY": "your_groq_api_key_here",
    "OPENAI_API_KEY": "your_openai_api_key_here",
    "OPENROUTER_API_KEY": "your_openrouter_api_key_here",
    "HUGGINGFACE_API_KEY": "your_huggingface_api_key_here"
}
```

> **Note:** You only need **at least one** API key to use the app. Alina automatically falls back to the next available provider if one fails.

### Supported LLM Providers & Models

| Provider | Models Used |
|---|---|
| **Groq** | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `gemma2-9b-it` |
| **OpenRouter** | `llama-3.3-70b-instruct:free`, `qwen2.5-72b:free`, `deepseek-chat:free` |
| **HuggingFace** | `Qwen2.5-72B`, `Llama-3.3-70B`, `DeepSeek-V3` |

---

## 🎯 Pronunciation Focus Areas

Alina specifically targets the most challenging areas for non-native English speakers:

- **TH sound** — *think, through, method, algorithm*
- **V vs W** — *very, website, version, workflow*
- **Ending consonants** — *worked, tests, projects, developed*
- **R sound (rhotic)** — *server, architecture, performance, error*
- **Sentence stress** — *"I built a web application"*
- **T-flap** — *better, water, letter, data*

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **UI Framework** | PyQt6 |
| **AI / LLM** | Groq, OpenRouter, HuggingFace (via OpenAI-compatible API) |
| **Text-to-Speech** | Microsoft Edge TTS (`edge_tts`) |
| **Speech-to-Text** | SoundDevice + SoundFile |
| **Audio Playback** | Pygame |
| **Packaging** | PyInstaller |

---

## 📊 How Progress is Tracked

Alina automatically saves your learning progress to:
```
%LOCALAPPDATA%\AlinaCoach\data\english_coach_progress.json
```

And logs all corrections and mistakes to:
```
%LOCALAPPDATA%\AlinaCoach\data\mistakes_log.txt
```

This data persists across sessions and is used to personalize your coaching.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Muhammad Haseeb Nawaz**
- GitHub: [@muhammadhaseebnawaz5](https://github.com/muhammadhaseebnawaz5)

---

<div align="center">
  <sub>Built with ❤️ to help people speak English with confidence.</sub>
</div>
