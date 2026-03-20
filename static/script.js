// Global variables
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let stream = null;
let audioContext = null;
let processor = null;
let lastStreamTranslation = '';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('App loaded');
    checkBrowserSupport();
});

// Handle record button click - check permissions first
async function handleRecordClick() {
    if (isRecording) {
        return; // Already recording
    }

    showStatus('Checking microphone permissions...');
    const hasPermission = await requestMicrophonePermission();

    if (hasPermission) {
        showStatus('Permissions granted. Starting recording...');
        await startRecording();
    }
}

// Check browser support for Web Audio API
function checkBrowserSupport() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) {
        showError('Your browser does not support Web Audio API');
    }

    // Check if getUserMedia is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showError('Your browser does not support microphone access. Please use a modern browser.');
    }
}

// Check microphone permission status
async function checkMicrophonePermission() {
    try {
        // Check if permission API is available
        if (navigator.permissions && navigator.permissions.query) {
            const permission = await navigator.permissions.query({ name: 'microphone' });
            return permission.state;
        }
        return 'unknown';
    } catch (error) {
        console.log('Permission API not supported');
        return 'unknown';
    }
}

// Request microphone permission
async function requestMicrophonePermission() {
    try {
        const permissionStatus = await checkMicrophonePermission();
        if (permissionStatus === 'denied') {
            showError('Microphone permission was denied. Please click the microphone icon in your browser\'s address bar and allow microphone access.');
            return false;
        }

        // Try to get user media briefly to trigger permission prompt
        const testStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        testStream.getTracks().forEach(track => track.stop()); // Stop immediately
        return true;
    } catch (error) {
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            showError('Microphone permission denied. Please click the microphone icon in your browser\'s address bar and allow microphone access.');
        } else {
            showError(`Permission check failed: ${error.message}`);
        }
        return false;
    }
}

// Start recording
async function startRecording() {
    try {
        // Check if we already have permission
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Initialize Web Audio API for proper audio processing
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(stream);

        // Create a processor to capture audio data
        processor = audioContext.createScriptProcessor(4096, 1, 1);
        audioChunks = [];

        processor.onaudioprocess = (event) => {
            if (isRecording) {
                const inputBuffer = event.inputBuffer;
                const inputData = inputBuffer.getChannelData(0);
                audioChunks.push(new Float32Array(inputData));
            }
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        isRecording = true;

        // Update UI
        document.getElementById('record-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
        showStatus('Recording... 🎤');
        clearError();

    } catch (error) {
        console.error('Recording error:', error);

        // Handle specific permission errors
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            showError('Microphone permission denied. Please click the microphone icon in your browser\'s address bar and allow microphone access, then try recording again.');
        } else if (error.name === 'NotFoundError') {
            showError('No microphone found. Please check your microphone connection and try again.');
        } else if (error.name === 'NotReadableError') {
            showError('Microphone is already in use by another application. Please close other applications using the microphone.');
        } else if (error.name === 'OverconstrainedError') {
            showError('Microphone does not support the required audio settings. Please try a different microphone.');
        } else if (error.name === 'NotSupportedError') {
            showError('Your browser does not support microphone access. Please use a modern browser like Chrome, Firefox, or Edge.');
        } else {
            showError(`Recording error: ${error.message}`);
        }

        // Reset recording state
        isRecording = false;
        document.getElementById('record-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
    }
}

// Stop recording
function stopRecording() {
    if (isRecording) {
        isRecording = false;

        // Stop Web Audio processing
        if (processor) {
            processor.disconnect();
            processor = null;
        }

        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        // Update UI
        document.getElementById('record-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
        showStatus('Processing audio...');

        // Process the recorded audio
        setTimeout(() => {
            handleRecordingStop();
        }, 100);
    }
}

// Convert Float32Array audio data to WAV format
function audioBufferToWav(buffer, sampleRate) {
    const length = buffer.length;
    const arrayBuffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(arrayBuffer);

    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * 2, true);

    // Convert float samples to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < length; i++) {
        const sample = Math.max(-1, Math.min(1, buffer[i]));
        view.setInt16(offset, sample * 0x7FFF, true);
        offset += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
}

// Handle recording stop
async function handleRecordingStop() {
    try {
        if (audioChunks.length === 0) {
            showError('No audio data recorded');
            return;
        }

        // Concatenate all audio chunks
        const totalLength = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const audioBuffer = new Float32Array(totalLength);
        let offset = 0;

        for (const chunk of audioChunks) {
            audioBuffer.set(chunk, offset);
            offset += chunk.length;
        }

        // Convert to WAV format
        const wavBlob = audioBufferToWav(audioBuffer, 16000);

        // Create FormData to send audio file
        const formData = new FormData();
        formData.append('file', wavBlob, 'recording.wav');

        // Send to backend for transcription
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            const sourceField = document.getElementById('source-text');
            sourceField.value = result.text;
            showStatus(`Transcribed: "${result.text}"`);
            // automatically translate after transcription
            translateText();
        } else {
            const error = await response.json();
            if (response.status === 400) {
                showError(`No speech detected. Please speak clearly and ensure your microphone is working.`);
            } else {
                showError(`Transcription failed: ${error.detail}`);
            }
        }
    } catch (error) {
        showError(`Error processing audio: ${error.message}`);
    } finally {
        // Clean up
        audioChunks = [];
        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }
    }
}

// Translate text
async function translateText() {
    const sourceText = document.getElementById('source-text').value.trim();
    const sourceLang = document.getElementById('source-lang').value;
    const targetLang = document.getElementById('target-lang').value;

    if (!sourceText) {
        showError('Please enter text to translate');
        return;
    }

    if (sourceLang === targetLang) {
        showError('Source and target languages must be different');
        return;
    }

    try {
        showStatus('Translating... 🔄');
        clearError();

        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: sourceText,
                source_language: sourceLang,
                target_language: targetLang
            })
        });

        if (response.ok) {
            const result = await response.json();
            document.getElementById('target-text').value = result.translated;
            showStatus(`Translation complete: "${result.translated}"`);

            // Automatically speak translation if enabled
            const autoSpeakElem = document.getElementById('auto-speak');
            if (autoSpeakElem && autoSpeakElem.checked) {
                speakTranslation();
            }
        } else {
            const error = await response.json();
            showError(`Translation failed: ${error.detail}`);
        }
    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

// Speak translation
function speakTranslation() {
    const translatedText = document.getElementById('target-text').value.trim();
    const targetLang = document.getElementById('target-lang').value;

    if (!translatedText) {
        showError('No translation to speak');
        return;
    }

    try {
        showStatus('Speaking translation... 🔊');
        clearError();

        // Cancel any currently speaking text to avoid overlap/repetition
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(translatedText);
        
        // Set language
        const langMap = {
            'en': 'en-US',
            'es': 'es-ES',
            'fr': 'fr-FR',
            'de': 'de-DE'
        };
        
        utterance.lang = langMap[targetLang] || 'en-US';
        utterance.rate = 1;
        utterance.pitch = 1;

        utterance.onend = () => {
            showStatus('Finished speaking');
        };

        utterance.onerror = (event) => {
            showError(`Speech error: ${event.error}`);
        };

        window.speechSynthesis.speak(utterance);

    } catch (error) {
        showError(`Error: ${error.message}`);
    }
}

// Clear text area
function clearText(elementId) {
    document.getElementById(elementId).value = '';
    showStatus('Text cleared');
}

// Copy to clipboard
async function copyToClipboard(elementId) {
    const text = document.getElementById(elementId).value;
    
    if (!text) {
        showError('Nothing to copy');
        return;
    }

    try {
        await navigator.clipboard.writeText(text);
        showStatus('✓ Copied to clipboard');
        
        // Reset message after 2 seconds
        setTimeout(() => {
            showStatus('Ready');
        }, 2000);
    } catch (error) {
        showError(`Copy failed: ${error.message}`);
    }
}

// Swap languages
function swapLanguages() {
    const sourceLang = document.getElementById('source-lang');
    const targetLang = document.getElementById('target-lang');
    
    // Swap language selections
    const temp = sourceLang.value;
    sourceLang.value = targetLang.value;
    targetLang.value = temp;

    // Swap text areas
    const sourceText = document.getElementById('source-text');
    const targetText = document.getElementById('target-text');
    
    const tempText = sourceText.value;
    sourceText.value = targetText.value;
    targetText.value = tempText;

    showStatus('Languages swapped');
}

// Show status message
function showStatus(message) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.style.display = 'block';
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = `⚠️ ${message}`;
    errorDiv.classList.add('show');
    errorDiv.style.display = 'block';
}

// Clear error message
function clearError() {
    const errorDiv = document.getElementById('error');
    errorDiv.classList.remove('show');
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
}

// Keyboard shortcuts
document.addEventListener('keydown', (event) => {
    // Ctrl+Enter to translate
    if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        translateText();
    }
    
    // Alt+R to record
    if (event.altKey && event.key === 'r') {
        event.preventDefault();
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }
});

// Auto-translate on source text change
const sourceArea = document.getElementById('source-text');
if (sourceArea) {
    sourceArea.addEventListener('input', () => {
        const txt = sourceArea.value.trim();
        if (txt) {
            translateText();
        } else {
            document.getElementById('target-text').value = '';
        }
    });
}

// Auto-translate when languages change
const sourceLangSelect = document.getElementById('source-lang');
const targetLangSelect = document.getElementById('target-lang');
const translateOnLanguageChange = () => {
    const txt = sourceArea?.value.trim();
    if (txt) translateText();
};
if (sourceLangSelect) sourceLangSelect.addEventListener('change', translateOnLanguageChange);
if (targetLangSelect) targetLangSelect.addEventListener('change', translateOnLanguageChange);

// ============ WebSocket Streaming Mode ============

let streamSocket = null;
let streamingActive = false;
let streamMediaRecorder = null;
let streamAudioContext = null;

async function startStreamingMode() {
    try {
        showStatus('Starting streaming mode...');
        clearError();
        
        // Request microphone permission
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Initialize WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        streamSocket = new WebSocket(protocol + '//' + window.location.host + '/ws/stream');

        streamSocket.onopen = () => {
            console.info('WebSocket connected');
            streamingActive = true;
            
            // Update UI
            document.getElementById('stream-btn').disabled = true;
            document.getElementById('stop-stream-btn').disabled = false;
            document.getElementById('stream-status').style.display = 'block';
            
            // Send configuration
            const config = {
                type: 'config',
                source_language: document.getElementById('source-lang').value,
                target_language: document.getElementById('target-lang').value
            };
            streamSocket.send(JSON.stringify(config));
            
            // Start recording
            initStreamRecording(stream);
            
            showStatus('Streaming active... Speak now!');
        };

        streamSocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'status') {
                updateStreamStatus(message.message);
            } else if (message.type === 'transcription') {
                document.getElementById('stream-transcription').textContent = message.text;
                document.getElementById('source-text').value = message.text;
            } else if (message.type === 'translation') {
                document.getElementById('stream-translation').textContent = message.text;
                document.getElementById('target-text').value = message.text;

                const autoSpeakElem = document.getElementById('auto-speak');
                if (autoSpeakElem && autoSpeakElem.checked && message.text && message.text !== lastStreamTranslation) {
                    speakTranslation();
                }
                lastStreamTranslation = message.text;
            } else if (message.type === 'audio') {
                const autoSpeakElem = document.getElementById('auto-speak');
                if (!autoSpeakElem || !autoSpeakElem.checked) {
                    playStreamAudio(message.data);
                }
            } else if (message.type === 'error') {
                showError(message.message);
                updateStreamStatus('Error: ' + message.message);
            }
        };

        streamSocket.onerror = (error) => {
            showError('WebSocket error: ' + error);
            streamingActive = false;
        };

        streamSocket.onclose = () => {
            console.info('WebSocket closed');
            stopStreamingMode();
        };

    } catch (error) {
        showError('Streaming error: ' + error.message);
        streamingActive = false;
    }
}

function initStreamRecording(stream) {
    streamMediaRecorder = new MediaRecorder(stream);
    
    streamMediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && streamSocket && streamingActive) {
            // Convert blob to base64 and send
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64 = reader.result.split(',')[1];
                streamSocket.send(JSON.stringify({
                    type: 'audio',
                    data: base64
                }));
            };
            reader.readAsDataURL(event.data);
        }
    };
    
    // Send audio chunks every 3 seconds (larger chunks improve transcription stability)
    streamMediaRecorder.start(3000);
}

function updateStreamStatus(message) {
    document.getElementById('stream-state').textContent = message;
}

function playStreamAudio(base64Audio) {
    try {
        const audioBlob = base64ToBlob(base64Audio, 'audio/wav');
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio();
        audio.src = audioUrl;
        audio.play();
    } catch (error) {
        showError('Audio playback error: ' + error.message);
    }
}

function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

function stopStreamingMode() {
    streamingActive = false;
    
    // Close media recorder
    if (streamMediaRecorder && streamMediaRecorder.state !== 'inactive') {
        streamMediaRecorder.stop();
    }
    
    // Stop all tracks
    if (streamMediaRecorder && streamMediaRecorder.stream) {
        streamMediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    // Close WebSocket
    if (streamSocket) {
        streamSocket.close();
        streamSocket = null;
    }
    
    // Update UI
    document.getElementById('stream-btn').disabled = false;
    document.getElementById('stop-stream-btn').disabled = true;
    document.getElementById('stream-status').style.display = 'none';
    
    showStatus('Streaming stopped');
}
