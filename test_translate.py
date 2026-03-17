import requests
import sys

# usage: python test_translate.py "some text" en es
text = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'hello'
src = sys.argv[2] if len(sys.argv) > 2 else 'en'
tgt = sys.argv[3] if len(sys.argv) > 3 else 'es'
resp = requests.post(
    'http://localhost:8000/api/translate',
    json={'text': text, 'source_language': src, 'target_language': tgt}
)
data = resp.json()
print(data)

# optionally invoke text-to-speech endpoint to ensure it's reachable
try:
    resp2 = requests.post(
        'http://localhost:8000/api/text-to-speech',
        json={'text': text, 'language': src}
    )
    print('tts response status', resp2.status_code)
except Exception as e:
    print('tts request failed', e)
"""
I have fixed the Whisper transcription failure by eliminating the direct dependency on ffmpeg
  for loading audio files.

  🛠️ Changes Implemented


   - Audio Loading Logic: Updated transcribe_with_whisper in main.py to use soundfile and
     librosa to load and resample audio into a 16kHz mono numpy array before passing it to the
     Whisper model. This bypasses Whisper's internal call to the ffmpeg command-line tool for
     audio loading.
   - Endpoint Robustness: Improved the /api/transcribe endpoint to correctly handle successful
     but empty transcriptions (e.g., silence), preventing unnecessary 500 Internal Server Error
     responses.
   - Lazy Imports: Moved audio processing imports (numpy, soundfile, librosa) to the top level
     for better performance and consistency.

  ✅ Verification Results


   - Reproduction: Confirmed that the original error ([WinError 2] The system cannot find the
     file specified) was caused by missing ffmpeg.
   - Validation: Verified the fix with a new test script (test_transcribe.py) which successfully
     transcribed audio through the running FastAPI server without requiring ffmpeg on the system
     path.
   - Compatibility: Ensured that the fallback to speech_recognition (Google API) remains intact
     if the Whisper model itself fails for other reasons.


  The system is now more portable and easier to deploy, especially on Windows environments where
  ffmpeg is not pre-installed.
"""