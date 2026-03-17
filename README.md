# Real-Time Voice Translator

A modern, fast, and easy-to-use real-time voice translation application built with **FastAPI** and modern web technologies.

## Features

✨ **Key Features:**
- 🎤 Real-time voice recording and transcription (powered by OpenAI Whisper)
- 🌍 Multi-language support (English, Spanish, French, German, and more)
- 🔄 Instant text translation
- 🔊 Text-to-speech with natural voices (Coqui TTS fallback to pyttsx3)
- 💬 WebSocket support for real-time communication
- 📱 Responsive design for desktop and mobile
- ⌨️ Keyboard shortcuts for faster operation
- 🔒 Secure API with CORS enabled

## Supported Languages

- **English (en)**
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Chinese (zh)
- Hindi (hi)

> Translations use a simple built-in phrase dictionary; for other text the
> service automatically falls back to a free online translator (MyMemory) or,
> when available, **Meta’s NLLB‑200 multilingual model** (via Hugging Face
> `transformers`) for hundreds of language pairs.

## Requirements

- Python 3.8+
- pip package manager
- Modern web browser with Web Audio API support
- Microphone access (for voice recording)
- (optional) GPU or enough RAM if using a large NLLB model

## Installation

### 2. Create and activate virtual environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Note: the `requirements.txt` now includes `transformers`, `sentencepiece`,
`accelerate` for NLLB, plus `openai-whisper` for speech-to-text and,
optionally, `TTS` (Coqui) for text-to-speech. Coqui TTS currently only
supports Python <3.12, so you may need to run the app in a 3.11 (or older)
environment to use that feature. A GPU is recommended for larger Whisper
models or NLLB variants.

### 1. Clone/Navigate to the project directory

```bash
cd d:\RealTImeVoiceTranslator2
```

### 2. Create and activate virtual environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Start the development server

```bash
python main.py
```

Or using Uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Access the application

Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

### 1. **Recording Voice**
   - Click "🎤 Start Recording" button
   - Speak clearly into your microphone
   - Click "⏹ Stop Recording" to finish
   - The text will be automatically transcribed (powered by Whisper when available)

*You can also POST an audio file to `/api/transcribe`; the server will run
OpenAI Whisper if installed or fall back to the original speech_recognition
logic.*

### 2. **Translating Text**
(To use the new Meta NLLB backend, set `NLLB_MODEL_NAME` in `.env` or
`config.py`.)

   - Select source and target languages
   - Enter or paste text (or use voice recording)
   - Click "🔄 Translate" button
   - View the translation result

### 3. **Speaking Translation**
   - After translation, click "🔊 Speak Translation"
   - The translation will be spoken aloud

### 4. **Keyboard Shortcuts**
   - `Ctrl + Enter` - Translate text
   - `Alt + R` - Start/Stop recording
   - `Ctrl + C` - Copy translation to clipboard

## API Endpoints

### GET `/`
Returns the main HTML interface

### POST `/api/transcribe`
Transcribe audio file to text
- **Request:** multipart/form-data with audio file
- **Response:** JSON with transcribed text and confidence

### POST `/api/translate`
Translate text between languages
- **Request Body:**
  ```json
  {
    "text": "Hello",
    "source_language": "en",
    "target_language": "es"
  }
  ```
- **Response:** JSON with translated text

### POST `/api/text-to-speech`
Convert text to speech
- **Request Body:**
  ```json
  {
    "text": "Hello",
    "language": "en"
  }
  ```

### GET `/api/health`
Health check endpoint
- **Response:** Service status information

### WebSocket `/ws/translator`
Real-time translation via WebSocket
- **Message Format:**
  ```json
  {
    "type": "translate",
    "text": "Hello",
    "source_language": "en",
    "target_language": "es"
  }
  ```

## Project Structure

```
RealTImeVoiceTranslator2/
├── main.py                 # FastAPI application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── README.md             # This file
├── .venv/                # Virtual environment
└── static/
    ├── index.html        # Main HTML interface
    ├── style.css         # Styling
    └── script.js         # Frontend JavaScript
```

## Configuration

### Environment Variables

Edit `.env` file to customize settings:

```env
DEBUG=False
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

### Settings

Modify `config.py` for advanced configuration:
- Language support
- Audio parameters
- TTS settings
- Supported languages

## Dependencies

Principal packages:
- **fastapi** (0.109.0) - Web framework
- **uvicorn** (0.27.0) - ASGI server
- **SpeechRecognition** (3.10.0) - Speech-to-text
- **pyttsx3** (2.90) - Text-to-speech
- **librosa** (0.10.0) - Audio processing
- **soundfile** (0.12.1) - Audio file handling
- **websockets** (12.0) - WebSocket support
- **pydantic** (2.5.3) - Data validation

For the complete list, see `requirements.txt`

## Troubleshooting

### Issue: "Could not understand audio"
- **Solution:** Ensure microphone is working and you're speaking clearly
- Try recording in a quiet environment

### Issue: "Could not connect to API"
- **Solution:** Make sure the server is running
- Check if port 8000 is available
- Verify firewall settings

### Issue: "Microphone access denied"
- **Solution:** Grant microphone permissions to the browser
- Check browser permissions settings

### Issue: "Module not found" error
- **Solution:** Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again

## Performance Tips

1. **Audio Quality:** Speak clearly and slowly for better recognition
2. **Network:** Use a stable internet connection for API calls
3. **Browser:** Use an updated web browser for best compatibility
4. **Memory:** Close unnecessary applications for better performance

## Browser Compatibility

- ✅ Chrome/Chromium 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Security Considerations

- The application runs on localhost by default
- For production: Change `SECRET_KEY` in `.env`
- Enable authentication and API keys if needed
- Use HTTPS for production deployments
- Implement rate limiting for public access

## Advanced Features

### WebSocket Real-time Translation
Connect to `/ws/translator` for real-time translation without page reload

### Custom Language Support
Add new language pairs in the `TRANSLATIONS` dictionary in `main.py`

### Database Integration
Configure `DATABASE_URL` to enable translation history and caching

## Deployment

### Using Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn (Production)

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## Performance Optimization

- Implement caching for frequently translated phrases
- Use async/await for non-blocking operations
- Optimize database queries
- Compress static assets
- Use CDN for static files

## Future Enhancements

- [ ] Integration with Google Translate API for better accuracy
- [ ] User authentication and history
- [ ] Offline translation support
- [ ] Mobile app version
- [ ] Voice cloning technology
- [ ] Multiple voice inputs simultaneously
- [ ] Translation history and bookmarks

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

This project is open-source and available under the MIT License.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ using FastAPI**
