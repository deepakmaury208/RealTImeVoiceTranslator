"""
Configuration file for Real-Time Voice Translator
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Application settings
APP_NAME = "Real-Time Voice Translator"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# API settings
API_TITLE = "Real-Time Voice Translator API"
API_DESCRIPTION = "FastAPI-based real-time voice translation service"
API_VERSION = "1.0.0"

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
RELOAD = os.getenv("RELOAD", "True").lower() == "true"

# Audio settings
AUDIO_SAMPLE_RATE = 16000  # Hz
AUDIO_CHUNK_SIZE = 4096  # bytes
AUDIO_FORMAT = "wav"

# Speech Recognition settings
SPEECH_RECOGNITION_ENGINE = "google"  # Options: google, sphinx

# Translation settings
MAX_TEXT_LENGTH = 5000  # characters
DEFAULT_SOURCE_LANGUAGE = "en"
DEFAULT_TARGET_LANGUAGE = "es"

# NLLB model configuration (Meta's No Language Left Behind)
NLLB_MODEL_NAME = os.getenv("NLLB_MODEL_NAME", "facebook/nllb-200-distilled-600M")

# Whisper configuration - improved for accuracy
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")  # Changed from "base" to "medium" for better accuracy
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu/cuda
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", None)  # Auto-detect if None

# Audio processing settings - optimized for latency
AUDIO_CHUNK_DURATION = 2.0  # seconds - reduced from 3 for lower latency
AUDIO_OVERLAP = 0.5  # seconds - overlap between chunks for continuity
AUDIO_MIN_CONFIDENCE = 0.7  # minimum confidence threshold

# Translation settings - improved accuracy
TRANSLATION_CACHE_SIZE = 1000  # Cache translations to reduce API calls
TRANSLATION_TIMEOUT = 3.0  # seconds - faster timeout

# TTS (Text-to-Speech) settings
TTS_ENGINE = "pyttsx3"  # Options: pyttsx3, google
TTS_RATE = 150  # Speech rate (words per minute)
COQUI_TTS_MODEL = "tts_models/en/ljspeech/vits"

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'hi': 'Hindi',
}

# CORS settings
CORS_ORIGINS = ["*"]
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Database settings (if needed in future)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./translator.db")

# Cache settings
CACHE_TRANSLATIONS = True
CACHE_TTL = 3600  # seconds

# Rate limiting
RATE_LIMIT_ENABLED = False
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = 60  # seconds

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
API_KEY_ENABLED = False
ALLOWED_API_KEYS = []

# File upload settings
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
UPLOAD_DIRECTORY = "uploads"
ALLOWED_AUDIO_FORMATS = ["wav", "mp3", "m4a", "ogg"]

# WebSocket settings
WS_TIMEOUT = 30  # seconds
WS_HEARTBEAT_INTERVAL = 30  # seconds

# Performance settings
WORKER_THREADS = 4
ASYNC_CONCURRENCY = 10
REQUEST_TIMEOUT = 30  # seconds

# Feature flags
ENABLE_AUDIO_RECORDING = True
ENABLE_WEBSOCKET = True
ENABLE_FILE_UPLOAD = True
ENABLE_HISTORY = False

# Storage settings
STORAGE_TYPE = "local"  # Options: local, s3, gcs
STORAGE_PATH = "storage"
