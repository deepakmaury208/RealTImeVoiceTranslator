# WebSocket streaming endpoint - add this after the existing websocket_translator endpoint

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming pipeline:
    audio chunks → Whisper → NLLB translation → Coqui TTS → audio response
    """
    await websocket.accept()
    try:
        config_data = None
        logger.info("WebSocket streaming client connected")
        
        while True:
            # Receive message (either config or audio chunk)
            message = await websocket.receive_json()
            
            if message.get("type") == "config":
                # initial configuration message with language settings
                config_data = {
                    "source_language": message.get("source_language", "en"),
                    "target_language": message.get("target_language", "es")
                }
                logger.info(f"Stream config: {config_data}")
                await websocket.send_json({
                    "type": "status",
                    "message": "Configuration received"
                })
                
            elif message.get("type") == "audio":
                # audio chunk in base64; decode and process
                if not config_data:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Configuration required before audio streaming"
                    })
                    continue
                
                try:
                    import base64
                    audio_data = base64.b64decode(message.get("data", ""))
                    
                    # Save temp file
                    temp_wav = f"temp_stream_{datetime.now().timestamp()}.wav"
                    with open(temp_wav, "wb") as f:
                        f.write(audio_data)
                    
                    try:
                        # 1. Transcribe with Whisper
                        await websocket.send_json({
                            "type": "status",
                            "message": "Transcribing..."
                        })
                        transcription = transcribe_with_whisper(temp_wav)
                        text = transcription.get("text", "")
                        logger.info(f"Transcribed: {text}")
                        
                        await websocket.send_json({
                            "type": "transcription",
                            "text": text
                        })
                        
                        # 2. Translate with NLLB
                        await websocket.send_json({
                            "type": "status",
                            "message": "Translating..."
                        })
                        translated = nllb_translate(
                            text,
                            config_data["source_language"],
                            config_data["target_language"]
                        )
                        logger.info(f"Translated: {translated}")
                        
                        await websocket.send_json({
                            "type": "translation",
                            "text": translated
                        })
                        
                        # 3. Generate speech with Coqui TTS
                        if CoquiTTS is not None:
                            await websocket.send_json({
                                "type": "status",
                                "message": "Generating speech..."
                            })
                            audio_file = make_tts(translated)
                            
                            # Read and send audio file as base64
                            with open(audio_file, "rb") as f:
                                audio_bytes = f.read()
                                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                            
                            await websocket.send_json({
                                "type": "audio",
                                "data": audio_b64
                            })
                            
                            # Clean up
                            try:
                                os.remove(audio_file)
                            except:
                                pass
                        else:
                            await websocket.send_json({
                                "type": "status",
                                "message": "Coqui TTS not available; using pyttsx3 fallback"
                            })
                        
                        await websocket.send_json({
                            "type": "status",
                            "message": "Complete"
                        })
                        
                    finally:
                        # Clean up temp wav file
                        try:
                            os.remove(temp_wav)
                        except:
                            pass
                        
                except Exception as e:
                    logger.error(f"Stream processing error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
    except Exception as e:
        logger.error(f"WebSocket streaming error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
