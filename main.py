import os
import wave
import asyncio
import base64
from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import speech_recognition as sr
import requests
import pyttsx3
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime
import numpy as np
try:
    import soundfile as sf
except ImportError:
    sf = None
try:
    import librosa
except ImportError:
    librosa = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

# configuration
import config

# Transformers for NLLB translation
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError:
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None

# globals for NLLB model
_nllb_tokenizer = None
_nllb_model = None

# Whisper speech-to-text
_whisper_model = None
try:
    import whisper
except ImportError:
    whisper = None

# Coqui TTS (text-to-speech)
_tts_coqui = None
try:
    from TTS.api import TTS as CoquiTTS
except ImportError:
    CoquiTTS = None


def load_nllb(model_name: str | None = None):
    """Lazy-load the NLLB tokenizer and model."""
    global _nllb_tokenizer, _nllb_model
    if model_name is None:
        model_name = config.NLLB_MODEL_NAME
    if _nllb_model is None:
        if AutoTokenizer is None or AutoModelForSeq2SeqLM is None:
            raise RuntimeError("Transformers library is not installed")
        _nllb_tokenizer = AutoTokenizer.from_pretrained(model_name)
        _nllb_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return _nllb_tokenizer, _nllb_model


def nllb_translate(text: str, src: str, tgt: str, model_name: str | None = None) -> str:
    """Translate text using NLLB. src and tgt are ISO lang codes (e.g. 'en','es')."""
    if not text or not text.strip():
        return ""
        
    
    nllb_codes = {
        'en': 'eng_Latn',
        'es': 'spa_Latn',
        'fr': 'fra_Latn',
        'de': 'deu_Latn',

        'it': 'ita_Latn',
        'pt': 'por_Latn',
        'ru': 'rus_Cyrl',
        'ja': 'jpn_Jpan',
        'zh': 'zho_Hans',
        'hi': 'hin_Deva',
    }
    
    src_code = nllb_codes.get(src, 'eng_Latn')
    tgt_code = nllb_codes.get(tgt, 'spa_Latn')
    
    try:
        tokenizer, model = load_nllb(model_name)
        tokenizer.src_lang = src_code
        
        inputs = tokenizer(text, return_tensors="pt")
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_code)
        
        outputs = model.generate(
            **inputs, 
            forced_bos_token_id=forced_bos_token_id, 
            max_length=200
        )
        
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"NLLB translation internal error: {e}")
        return text


def load_whisper(model_name: str | None = None):
    """Load Whisper model lazily."""
    global _whisper_model
    if whisper is None:
        raise RuntimeError("Whisper library is not installed")
    if model_name is None:
        model_name = config.WHISPER_MODEL
    if _whisper_model is None:
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model


def transcribe_with_whisper(wav_path: str, language: str | None = None) -> dict:
    """Transcribe audio with Whisper, with fallback to speech_recognition."""
    try:
        model = load_whisper()
        
        # Load audio
        if AudioSegment is not None:
            # Use pydub to load audio regardless of format
            audio_segment = AudioSegment.from_file(wav_path)
            # Convert to mono, 16kHz
            audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
            # Get raw audio data as numpy array
            audio_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768.0  # Normalize to [-1, 1]
            audio_input = audio_data
        elif sf is not None and librosa is not None:
            # Fallback to soundfile if pydub not available
            audio_data, sample_rate = sf.read(wav_path, dtype='float32')
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            if sample_rate != 16000:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
            audio_input = audio_data
        else:
            # Last resort: pass path directly (requires ffmpeg)
            audio_input = wav_path

        options = {}
        if language:
            options['language'] = language
        
        result = model.transcribe(audio_input, **options)
        return result
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        # Fallback to speech_recognition (Google) if Whisper fails
        try:
            logger.info("Using speech_recognition as fallback...")
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            return {"text": text, "fallback": True}
        except Exception as fallback_err:
            logger.error(f"Transcription fallback also failed: {fallback_err}")
            return {"text": "", "error": str(e)}


def make_tts(text: str) -> str:
    """Generate speech audio using Coqui TTS and return file path."""
    global _tts_coqui
    if CoquiTTS is None:
        raise RuntimeError("Coqui TTS library is not installed")
    if _tts_coqui is None:
        _tts_coqui = CoquiTTS(model_name=config.COQUI_TTS_MODEL)
    out_file = f"tts_{datetime.now().timestamp()}.wav"
    _tts_coqui.tts_to_file(text=text, file_path=out_file)
    return out_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Real-Time Voice Translator")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize speech recognizer and text-to-speech engine
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# Serve static files
if not os.path.exists('static'):
    os.makedirs('static')

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Pydantic models
class TextToSpeechRequest(BaseModel):
    text: str
    language: str = "en"

class TranslationRequest(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str = "es"

# Dictionary for lang codes
LANGUAGE_CODES = {
    'en': 'en-US',
    'es': 'es-ES',
    'fr': 'fr-FR',
    'de': 'de-DE',
    'it': 'it-IT',
    'pt': 'pt-BR',
    'ru': 'ru-RU',
    'ja': 'ja-JP',
    'zh': 'zh-CN',
    'hi': 'hi-IN',
}

# external translator (fallback)
translator = None
try:
    from googletrans import Translator
    translator = Translator()
except Exception as e:
    # anything can fail (e.g. incompatible httpcore)
    logger.warning(f"googletrans not available: {e}")
    translator = None

# Simple translation simulation using dictionary
TRANSLATIONS = {
    ('en', 'es'): {
        'hello': 'hola',
        'goodbye': 'adiós',
        'thank you': 'gracias',
        'please': 'por favor',
        'how are you': 'cómo estás',
        'good morning': 'buenos días',
        'good night': 'buenas noches',
        'my name is': 'mi nombre es',
        'what is your name': 'cuál es tu nombre',
        'nice to meet you': 'mucho gusto',
    },
    ('en', 'fr'): {
        'hello': 'bonjour',
        'goodbye': 'au revoir',
        'thank you': 'merci',
        'please': 's\'il vous plaît',
        'how are you': 'comment allez-vous',
        'good morning': 'bonjour',
        'good night': 'bonne nuit',
        'my name is': 'mon nom est',
        'what is your name': 'quel est votre nom',
        'nice to meet you': 'enchanté',
    }
}

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Template file not found</h1>", status_code=500)

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio file to text"""
    temp_file = None
    wav_file = None
    try:
        contents = await file.read()
        temp_file = f"temp_{datetime.now().timestamp()}_{file.filename}"
        with open(temp_file, "wb") as f:
            f.write(contents)

        try:
            import soundfile as sf
            import numpy as np
            import librosa

            audio_data, sample_rate = sf.read(temp_file)
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            if sample_rate != 16000:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000

            wav_file = f"temp_{datetime.now().timestamp()}.wav"
            sf.write(wav_file, audio_data, sample_rate, format='WAV')
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            wav_file = temp_file

        # Whisper with internal fallback
        result = transcribe_with_whisper(wav_file)
        if "error" not in result:
            return {
                "text": result.get("text", ""),
                "confidence": 1.0,
                "timestamp": datetime.now().isoformat(),
                "fallback": result.get("fallback", False)
            }
        else:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {result.get('error')}")

    finally:
        for f in [wav_file, temp_file]:
            if f and os.path.exists(f):
                try: os.remove(f)
                except: pass

@app.post("/api/translate")
async def translate(request: TranslationRequest):
    """Translate text from source to target language"""
    try:
        source_text = request.text.lower().strip()
        source_lang = request.source_language
        target_lang = request.target_language
        
        # 1. Dictionary
        key = (source_lang, target_lang)
        if key in TRANSLATIONS:
            for phrase, translation in TRANSLATIONS[key].items():
                if phrase in source_text:
                    return {"translated": translation, "method": "dictionary"}
        
        # 2. GoogleTrans
        if translator:
            try:
                t = translator.translate(request.text, src=source_lang, dest=target_lang)
                return {"translated": t.text, "method": "googletrans"}
            except: pass

        # 3. MyMemory
        try:
            params = {'q': request.text, 'langpair': f"{source_lang}|{target_lang}"}
            resp = requests.get('https://api.mymemory.translated.net/get', params=params, timeout=5)
            if resp.status_code == 200:
                translated = resp.json().get('responseData', {}).get('translatedText')
                if translated: return {"translated": translated, "method": "mymemory"}
        except: pass
        
        # 4. NLLB
        try:
            translated = nllb_translate(request.text, source_lang, target_lang)
            return {"translated": translated, "method": "nllb"}
        except: pass

        return {"translated": request.text, "method": "none"}
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    try:
        if CoquiTTS is not None:
            audio_file = make_tts(request.text)
            return FileResponse(audio_file, media_type="audio/wav")
        else:
            tts_engine.say(request.text)
            tts_engine.runAndWait()
            return {"status": "success"}
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        config_data = None
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "config":
                config_data = message
                await websocket.send_json({"type": "status", "message": "Ready"})
            elif message.get("type") == "audio":
                if not config_data: continue
                audio_data = base64.b64decode(message.get("data", ""))
                temp_wav = f"temp_stream_{datetime.now().timestamp()}.wav"
                with open(temp_wav, "wb") as f: f.write(audio_data)
                try:
                    # Transcribe (with internal fallback)
                    trans = transcribe_with_whisper(temp_wav)
                    text = trans.get("text", "")
                    await websocket.send_json({"type": "transcription", "text": text})
                    
                    if not text: continue

                    # Translate
                    translated_data = await translate(TranslationRequest(
                        text=text, 
                        source_language=config_data.get("source_language", "en"),
                        target_language=config_data.get("target_language", "es")
                    ))
                    translated = translated_data["translated"]
                    await websocket.send_json({"type": "translation", "text": translated})
                    
                    # TTS
                    if CoquiTTS:
                        audio_file = make_tts(translated)
                        with open(audio_file, "rb") as f:
                            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                        await websocket.send_json({"type": "audio", "data": audio_b64})
                        try: os.remove(audio_file)
                        except: pass
                finally:
                    try: os.remove(temp_wav)
                    except: pass
    except Exception as e:
        logger.error(f"Stream error: {e}")
    finally:
        try: await websocket.close()
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
