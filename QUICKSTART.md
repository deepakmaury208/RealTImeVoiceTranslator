# Quick Start Guide - Real-Time Voice Translator

## ⚡ Quick Setup (5 Minutes)

### Step 1: Verify Installation ✓
All dependencies are already installed! You can see them in `requirements.txt`

Installed packages:
- 🎩 FastAPI (Web framework)
- 🏃 Uvicorn (ASGI server)
- 🎤 SpeechRecognition (voice-to-text)
- 🔊 pyttsx3 (text-to-speech)
- 🌐 websockets (real-time communication)
- 📚 librosa (audio processing)
- And more!

### Step 2: Virtual Environment
Your virtual environment is ready in `/venv` folder

### Step 3: Run the Application

**On Windows:**
```bash
# Double-click run.bat file, OR
# In PowerShell/CMD:
.venv\Scripts\activate
python main.py
```

**On macOS/Linux:**
```bash
# Make script executable
chmod +x run.sh

# Run the application
./run.sh
# OR manually:
source .venv/bin/activate
python main.py
```

**Or use Uvicorn directly:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Access the Application
Open your browser and go to:
```
http://localhost:8000
```

You should see the Real-Time Voice Translator interface! 🎉

---

## 🎯 How to Use

### 1. Record Voice
- Click **"🎤 Start Recording"** button
- Speak clearly into your microphone
- Click **"⏹ Stop Recording"** when done
- Text appears instantly

### 2. Translate
- Select **Source Language** (English, Spanish, French, etc.)
- Select **Target Language**
- Click **"🔄 Translate"**
- Get instant translation!

### 3. Listen
- Click **"🔊 Speak Translation"**
- Hear the translation in the target language

### 4. Copy Result
- Click **"📋 Copy"** to copy translation to clipboard

---

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Translate text |
| `Alt + R` | Start/Stop recording |
| `Ctrl + C` | Copy to clipboard |

---

## 📁 Project Files

```
RealTImeVoiceTranslator2/
├── main.py              ← Main FastAPI application
├── config.py            ← Configuration settings
├── requirements.txt     ← Python dependencies (installed ✓)
├── .env                 ← Environment variables
├── run.bat             ← Windows launcher
├── run.sh              ← Linux/macOS launcher
├── README.md           ← Full documentation
├── QUICKSTART.md       ← This file
└── static/
    ├── index.html      ← Web interface HTML
    ├── style.css       ← Styling
    └── script.js       ← Frontend logic
```

---

## 🔍 Main API Endpoints

Your FastAPI server provides these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Main web interface |
| `/api/transcribe` | POST | Voice to text |
| `/api/translate` | POST | Translate text |
| `/api/text-to-speech` | POST | Text to voice |
| `/api/health` | GET | Server health check |
| `/ws/translator` | WebSocket | Real-time translation |

---

## 🆘 Troubleshooting

### "ModuleNotFoundError" error?
```bash
# Ensure virtual environment is activated:
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Then reinstall packages:
pip install -r requirements.txt
```

### Microphone not working?
1. Check browser permissions (allow microphone access)
2. Verify microphone is connected and working
3. Try in a different browser (Chrome is recommended)

### Port 8000 already in use?
```bash
# Use a different port:
uvicorn main:app --port 8001
# Then access: http://localhost:8001
```

### Server won't start?
1. Check if port 8000 is available: `netstat -an | find ":8000"`
2. Close any other applications using port 8000
3. Try restarting the server

---

## 🚀 Next Steps

1. **Test the translator** - Try recording and translating some phrases
2. **Customize settings** - Edit `config.py` for advanced options
3. **Add more languages** - Add translation pairs in `main.py`
4. **Deploy** - See README.md for production deployment

---

## 📞 Support

- Check README.md for detailed documentation
- Review config.py for available settings
- Check browser console (F12) for any JavaScript errors

---

## 🎉 Success!

Your Real-Time Voice Translator is now ready to use!

Happy translating! 🌍

---

**Created with ❤️ using FastAPI**
