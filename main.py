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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# configuration
import config

# Transformers for NLLB translation
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError:
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None

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

# globals for NLLB model
_nllb_tokenizer = None
_nllb_model = None

# external translator (fallback)
translator = None
try:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator
except Exception as e:
    logger.warning(f"deep_translator not available: {e}")
    translator = None

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

# Core Translation Logic
async def perform_translation(text: str, source_lang: str, target_lang: str) -> dict:
    """Core translation logic used by both API and cache."""
    try:
        source_text = (text or "").strip()

        if not source_text:
            return {"translated": "", "method": "none"}

        # 1. NLLB first (preferred pipeline for speed/accuracy)
        try:
            translated = await asyncio.to_thread(nllb_translate, text, source_lang, target_lang)
            if translated and translated.strip() and translated.strip().lower() != source_text.lower():
                return {"translated": translated, "method": "nllb"}
        except Exception as nllb_err:
            logger.warning(f"NLLB translation failed: {nllb_err}")

        # 2. Dictionary fallback for common phrases
        key = (source_lang, target_lang)
        if key in TRANSLATIONS:
            for phrase, translation in TRANSLATIONS[key].items():
                if phrase in source_text.lower():
                    return {"translated": translation, "method": "dictionary"}

        # 3. Remote translation (preferred when using remote mode)
        if config.USE_REMOTE_MODE and config.REMOTE_TRANSLATE_URL:
            try:
                resp = requests.post(
                    config.REMOTE_TRANSLATE_URL,
                    json={"text": text, "source_language": source_lang, "target_language": target_lang},
                    timeout=10
                )
                resp.raise_for_status()
                translated = resp.json().get("translated")
                if translated:
                    return {"translated": translated, "method": "remote-translate"}
            except Exception as e:
                logger.warning(f"Remote translate failed: {e}")

        # 4. Optional online fallbacks only when Coqui TTS is not present
        if CoquiTTS is None:
            if translator:
                try:
                    t = translator(source=source_lang, target=target_lang)
                    translated = t.translate(text)
                    return {"translated": translated, "method": "google-translate"}
                except Exception as google_err:
                    logger.warning(f"Google translate failed: {google_err}")

            try:
                params = {'q': text, 'langpair': f"{source_lang}|{target_lang}"}
                resp = requests.get('https://api.mymemory.translated.net/get', params=params, timeout=3)
                if resp.status_code == 200:
                    translated = resp.json().get('responseData', {}).get('translatedText')
                    if translated:
                        return {"translated": translated, "method": "mymemory"}
            except Exception as mymemory_err:
                logger.warning(f"MyMemory translate failed: {mymemory_err}")

        # 4. Finally fallback to original text
        return {"translated": text, "method": "none"}
    except Exception as e:
        logger.error(f"Core translation error: {str(e)}")
        return {"translated": text, "method": "error", "error": str(e)}

# Translation cache for improved latency
_translation_cache = {}
_cache_lock = asyncio.Lock()

async def cached_translate(request: TranslationRequest) -> dict:
    """Cached translation with improved latency."""
    cache_key = f"{request.text.lower().strip()}|{request.source_language}|{request.target_language}"

    async with _cache_lock:
        if cache_key in _translation_cache:
            return _translation_cache[cache_key]

    # Perform translation
    result = await perform_translation(request.text, request.source_language, request.target_language)

    # Cache the result
    async with _cache_lock:
        if len(_translation_cache) >= getattr(config, 'TRANSLATION_CACHE_SIZE', 100):
            oldest_keys = list(_translation_cache.keys())[:len(_translation_cache)//4]
            for key in oldest_keys:
                del _translation_cache[key]
        _translation_cache[cache_key] = result

    return result

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
    logger.warning("Coqui TTS not available - using browser TTS only")


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
    """Transcribe audio with Whisper (local) or remote server when remote mode enabled."""
    if config.USE_REMOTE_MODE and config.REMOTE_TRANSCRIBE_URL:
        try:
            with open(wav_path, "rb") as audio_file:
                files = {"file": audio_file}
                data = {"language": language} if language else {}
                resp = requests.post(config.REMOTE_TRANSCRIBE_URL, files=files, data=data, timeout=20)
            resp.raise_for_status()
            result = resp.json()
            return {
                "text": result.get("text", ""),
                "confidence": float(result.get("confidence", 0.5)),
                "language": result.get("language", language or "en")
            }
        except Exception as exc:
            logger.warning(f"Remote transcription failed: {exc}")
            # fallback to local whisper path if available

    try:
        model = load_whisper()
        audio_input = wav_path

        if AudioSegment is not None:
            try:
                audio_segment = AudioSegment.from_file(wav_path)
                audio_segment = audio_segment.normalize()
                audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
                audio_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                max_val = np.max(np.abs(audio_data))
                if max_val > 0:
                    audio_data = audio_data / max_val
                audio_input = audio_data
            except Exception as pydub_err:
                logger.warning(f"Pydub preprocessing failed: {pydub_err}")
                audio_input = wav_path
        elif sf is not None and librosa is not None:
            try:
                audio_data, sample_rate = sf.read(wav_path, dtype='float32')
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                if sample_rate != 16000:
                    audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                audio_input = audio_data
            except Exception as sf_err:
                logger.warning(f"Soundfile preprocessing failed: {sf_err}")
                audio_input = wav_path

        options = {
            'temperature': [0.0, 0.2, 0.4],
            'best_of': 5,
            'beam_size': 5,
        }

        if language:
            options['language'] = language
        elif getattr(config, 'WHISPER_LANGUAGE', None):
            options['language'] = config.WHISPER_LANGUAGE

        result = model.transcribe(audio_input, **options)

        if 'segments' in result and result['segments']:
            confidences = [seg.get('avg_logprob', 0) for seg in result['segments']]
            avg_confidence = np.mean(confidences) if confidences else 0
            confidence_score = min(1.0, max(0.0, (avg_confidence + 4) / 4))
            result['confidence'] = confidence_score
        else:
            result['confidence'] = 0.5

        return result

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        is_wav = False
        try:
            with open(wav_path, 'rb') as f:
                if f.read(4) == b'RIFF': is_wav = True
        except: pass

        if is_wav:
            try:
                logger.info("Using speech_recognition as fallback...")
                with sr.AudioFile(wav_path) as source:
                    audio = recognizer.record(source)
                    text = recognizer.recognize_google(audio, language=language) if language else recognizer.recognize_google(audio)
                return {"text": text, "fallback": True, "confidence": 0.6}
            except Exception as fallback_err:
                logger.error(f"Transcription fallback failed: {fallback_err}")
                return {"text": "", "error": str(e), "confidence": 0.0}
        return {"text": "", "error": str(e), "confidence": 0.0}


def make_tts(text: str) -> str:
    """Generate speech audio and return wav file path."""
    global _tts_coqui
    out_file = f"tts_{datetime.now().timestamp()}.wav"

    if config.USE_REMOTE_MODE and config.REMOTE_TTS_URL:
        try:
            resp = requests.post(
                config.REMOTE_TTS_URL,
                json={"text": text},
                timeout=20
            )
            resp.raise_for_status()
            with open(out_file, "wb") as f:
                f.write(resp.content)
            return out_file
        except Exception as e:
            logger.warning(f"Remote TTS failed: {e}")

    if CoquiTTS is not None:
        # Preferred path: Coqui TTS
        if _tts_coqui is None:
            _tts_coqui = CoquiTTS(model_name=config.COQUI_TTS_MODEL)
        _tts_coqui.tts_to_file(text=text, file_path=out_file)
        return out_file

    # Fallback: pyttsx3 local engine (Windows friendly) if Coqui is not available
    try:
        tts_engine = pyttsx3.init()
        tts_engine.setProperty('rate', config.TTS_RATE)
        tts_engine.save_to_file(text, out_file)
        tts_engine.runAndWait()
        return out_file
    except Exception as e:
        logger.warning(f"pyttsx3 fallback TTS failed: {e}")
        raise

# Initialize FastAPI app
app = FastAPI(title="Real-Time Voice Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

if not os.path.exists('static'):
    os.makedirs('static')

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Template file not found</h1>", status_code=500)

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_file = None
    wav_file = None
    try:
        contents = await file.read()
        temp_file = f"temp_{datetime.now().timestamp()}_{file.filename}"
        with open(temp_file, "wb") as f: f.write(contents)

        try:
            audio_data, sample_rate = sf.read(temp_file)
            if len(audio_data.shape) > 1: audio_data = np.mean(audio_data, axis=1)
            if sample_rate != 16000:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000
            wav_file = f"temp_{datetime.now().timestamp()}.wav"
            sf.write(wav_file, audio_data, sample_rate, format='WAV')
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            wav_file = temp_file

        result = transcribe_with_whisper(wav_file)
        if "error" not in result:
            return {
                "text": result.get("text", ""),
                "confidence": result.get("confidence", 1.0),
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
    result = await perform_translation(request.text, request.source_language, request.target_language)
    if result.get("method") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

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
    audio_buffer = bytearray()
    try:
        config_data = None
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "config":
                config_data = message
                audio_buffer = bytearray()
                await websocket.send_json({"type": "status", "message": "Ready"})
            elif message.get("type") == "audio":
                if not config_data:
                    continue
                new_data = base64.b64decode(message.get("data", ""))
                # Save raw chunk and try explicit conversion to WAV before Whisper
                temp_input = f"temp_stream_{datetime.now().timestamp()}.webm"
                temp_wav = f"temp_stream_{datetime.now().timestamp()}.wav"
                with open(temp_input, "wb") as f:
                    f.write(new_data)

                audio_for_whisper = temp_input
                if AudioSegment is not None:
                    try:
                        segment = AudioSegment.from_file(temp_input)
                        segment = segment.set_channels(1).set_frame_rate(16000).normalize()
                        segment.export(temp_wav, format="wav")
                        audio_for_whisper = temp_wav
                    except Exception as pydub_convert_err:
                        logger.warning(f"Audio chunk conversion failed ({temp_input}): {pydub_convert_err}")
                        audio_for_whisper = temp_input

                try:
                    start_time = asyncio.get_event_loop().time()
                    trans_start = asyncio.get_event_loop().time()
                    trans = transcribe_with_whisper(audio_for_whisper, config_data.get("source_language"))
                    trans_time = asyncio.get_event_loop().time() - trans_start
                    text = trans.get("text", "").strip()
                    confidence = trans.get("confidence", 0.5)
                    detected_lang = trans.get("language", config_data.get("source_language", "en"))

                    min_confidence = getattr(config, 'AUDIO_MIN_CONFIDENCE', 0.4)
                    if text:
                        # Always send interim transcription to show live updates
                        await websocket.send_json({"type": "transcription", "text": text, "confidence": round(confidence, 2)})

                        # Even on low confidence, continue with translation for conversational feel
                        if confidence >= min_confidence or confidence >= 0.25:
                            translate_start = asyncio.get_event_loop().time()
                            translated_data = await cached_translate(TranslationRequest(
                                text=text,
                                source_language=detected_lang,
                                target_language=config_data.get("target_language", "es")
                            ))
                            translate_time = asyncio.get_event_loop().time() - translate_start
                            translated = translated_data.get("translated", "")
                            await websocket.send_json({"type": "translation", "text": translated, "partial": True})

                            if CoquiTTS and confidence >= 0.6:
                                tts_start = asyncio.get_event_loop().time()
                                audio_file = await asyncio.to_thread(make_tts, translated)
                                try:
                                    with open(audio_file, "rb") as f:
                                        audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                                    await websocket.send_json({"type": "audio", "data": audio_b64})
                                finally:
                                    try:
                                        os.remove(audio_file)
                                    except:
                                        pass
                                tts_time = asyncio.get_event_loop().time() - tts_start

                        total_time = asyncio.get_event_loop().time() - start_time
                        await websocket.send_json({
                            "type": "performance",
                            "transcription_time": round(trans_time, 2),
                            "translation_time": round(translate_time, 2),
                            "tts_time": round(locals().get('tts_time', 0), 2),
                            "total_time": round(total_time, 2),
                            "confidence": round(confidence, 2)
                        })
                    else:
                        await websocket.send_json({"type": "status", "message": f"No text detected yet (confidence {confidence:.2f})"})
                finally:
                    for fpath in [temp_input, temp_wav]:
                        try:
                            if os.path.exists(fpath):
                                os.remove(fpath)
                        except:
                            pass
    except Exception as e:
        logger.error(f"Stream error: {e}")
    finally:
        try: await websocket.close()
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
