# OpenAI Realtime API Integration Guide

## Overview

This document describes the integration of OpenAI's Realtime API with Twilio Media Streams for low-latency voice conversations.

## Architecture

```
┌─────────────────┐
│   User's Phone  │
└────────┬────────┘
         │ Phone Call (Voice)
         ▼
┌─────────────────────────────────┐
│      Twilio Platform            │
│  ┌──────────────────────────┐   │
│  │  Voice Call Management   │   │
│  │  - Call routing          │   │
│  │  - Audio encoding        │   │
│  │    (mulaw 8kHz)          │   │
│  └──────────────────────────┘   │
└────────┬────────────────────────┘
         │ HTTP POST
         ▼
┌─────────────────────────────────┐
│   Flask HTTP Server (3000)      │
│  ┌──────────────────────────┐   │
│  │  /voice/initial          │   │
│  │  Returns TwiML with      │   │
│  │  <Stream> instruction    │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
         │
         │ TwiML Response: Connect to WebSocket
         ▼
┌─────────────────────────────────┐
│  WebSocket Server (3001)        │
│  ┌──────────────────────────┐   │
│  │  Media Stream Handler    │   │
│  │  - Receive mulaw audio   │   │
│  │  - Convert to PCM16      │   │
│  │  - Send to OpenAI        │   │
│  │  - Receive PCM16 audio   │   │
│  │  - Convert to mulaw      │   │
│  │  - Send to Twilio        │   │
│  └──────────────────────────┘   │
└────────┬────────────────────────┘
         │ WebSocket (audio stream)
         ▼
┌─────────────────────────────────┐
│   OpenAI Realtime API           │
│  wss://api.openai.com/v1/       │
│         realtime                │
│  ┌──────────────────────────┐   │
│  │  - Speech-to-speech AI   │   │
│  │  - Context management    │   │
│  │  - Voice Activity Detect │   │
│  │  - Natural TTS           │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

## Key Components

### 1. Realtime API Client (`src/services/realtime_client.py`)

**Purpose**: Manages WebSocket connection to OpenAI Realtime API

**Key Features**:
- Persistent WebSocket connection
- Session configuration with instructions
- Audio streaming (send/receive)
- Event handling (transcription, audio, errors)

**Configuration**:
```python
{
    "modalities": ["text", "audio"],
    "instructions": "System prompt for AI behavior",
    "voice": "alloy",  # Voice selection
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16",
    "turn_detection": {
        "type": "server_vad",  # Voice Activity Detection
        "threshold": 0.5,
        "silence_duration_ms": 500
    }
}
```

### 2. Media Stream Handler (`src/services/media_stream_handler.py`)

**Purpose**: Bridges Twilio Media Streams and OpenAI Realtime API

**Key Responsibilities**:
- Accept WebSocket connections from Twilio
- Process Twilio Media Stream events
- Convert audio formats (mulaw ↔ PCM16)
- Relay audio bidirectionally
- Handle connection lifecycle

**Message Flow**:

**From Twilio**:
```json
{
  "event": "media",
  "media": {
    "payload": "base64_encoded_mulaw_audio"
  }
}
```

**To OpenAI**:
```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64_encoded_pcm16_audio"
}
```

**From OpenAI**:
```json
{
  "type": "response.audio.delta",
  "delta": "base64_encoded_pcm16_audio"
}
```

**To Twilio**:
```json
{
  "event": "media",
  "streamSid": "MZ...",
  "media": {
    "payload": "base64_encoded_mulaw_audio"
  }
}
```

### 3. Audio Converter (`src/utils/audio_converter.py`)

**Purpose**: Convert between audio formats

**Conversions**:
- `mulaw_to_pcm16()` - Twilio format → OpenAI format
- `pcm16_to_mulaw()` - OpenAI format → Twilio format
- Base64 encoding/decoding

**Technical Details**:
- Twilio: mulaw 8kHz, 8-bit
- OpenAI: PCM16 8kHz (or 24kHz), 16-bit
- Uses Python `audioop` module for conversion

### 4. WebSocket Server (`src/websocket_server.py`)

**Purpose**: Standalone WebSocket server for Media Streams

**Configuration**:
- Port: 3001 (configurable as PORT + 1)
- Protocol: WebSocket (ws:// or wss://)
- Ping interval: 20 seconds

## Event Flow

### Call Initiation

1. User runs: `python src/scripts/make_call.py +79991234567`
2. Script calls Twilio API to initiate call
3. Twilio calls webhook: `POST /voice/initial`
4. Flask returns TwiML:
```xml
<Response>
  <Connect>
    <Stream url="wss://your-domain.com:3001/media-stream"/>
  </Connect>
</Response>
```

### WebSocket Setup

5. Twilio establishes WebSocket to our server
6. Media Stream Handler receives "start" event:
```json
{
  "event": "start",
  "streamSid": "MZ...",
  "start": {
    "callSid": "CA..."
  }
}
```

7. Handler connects to OpenAI Realtime API:
```
wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01
```

### Conversation Loop

8. **User speaks** → Phone captures audio
9. **Twilio** → Encodes to mulaw, sends via WebSocket
10. **Media Handler** → Converts mulaw to PCM16
11. **OpenAI** → Processes audio with AI
12. **OpenAI** → Generates response audio (PCM16)
13. **Media Handler** → Converts PCM16 to mulaw
14. **Twilio** → Plays audio to user
15. Repeat steps 8-14 until call ends

### Call Termination

16. User hangs up or conversation ends
17. Twilio sends "stop" event
18. Media Handler closes OpenAI connection
19. Cleanup: conversation history cleared

## Realtime API Features

### Voice Activity Detection (VAD)

Automatically detects when user stops speaking:

```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,          # Sensitivity (0-1)
    "prefix_padding_ms": 300,  # Audio before speech
    "silence_duration_ms": 500 # Silence to detect end
}
```

### Session Management

Each call gets isolated session:
- Unique conversation history
- Custom instructions
- Automatic cleanup on disconnect

### Audio Transcription

Optional transcription of user speech:

```python
"input_audio_transcription": {
    "model": "whisper-1"
}
```

Received as events:
```json
{
  "type": "conversation.item.input_audio_transcription.completed",
  "transcript": "Здравствуйте, хочу узнать о работе водителем"
}
```

### Interrupt Support

User can interrupt AI mid-sentence:
- AI detects new user speech
- Stops current response
- Processes new input immediately

## Performance Characteristics

### Latency Breakdown

- **Network latency**: 50-100ms (regional)
- **AI processing**: 200-300ms (Realtime API)
- **Audio encoding/decoding**: <10ms
- **Total**: ~300-400ms (vs 2-3s for traditional approach)

### Audio Quality

- Sample rate: 8kHz (phone quality)
- Bit depth: 16-bit PCM (lossless from mulaw)
- Codec: mulaw (Twilio) → PCM16 (OpenAI) → mulaw (Twilio)

### Scalability

**Current limitations**:
- One WebSocket per call
- In-memory conversation storage
- No call queueing

**Recommended for scale**:
- Use Redis for session storage
- Implement connection pooling
- Add load balancer for WebSocket servers
- Monitor active connections

## Error Handling

### Connection Errors

```python
try:
    await websockets.connect(url)
except Exception as e:
    logger.error(f"Failed to connect: {e}")
    # Return error to caller
```

### Audio Conversion Errors

```python
try:
    pcm_audio = mulaw_to_pcm16(audio_data)
except Exception as e:
    logger.error(f"Audio conversion failed: {e}")
    # Skip frame, continue stream
```

### OpenAI API Errors

```json
{
  "type": "error",
  "error": {
    "message": "Rate limit exceeded",
    "code": "rate_limit_error"
  }
}
```

Handled gracefully:
- Log error
- Optionally retry
- Inform user if critical

## Security Considerations

### Authentication

- **OpenAI**: Bearer token in WebSocket header
- **Twilio**: Webhook signature verification (TODO)

### Data Privacy

- Audio streams not recorded by default
- Conversation history cleared on disconnect
- No PII stored permanently

### Network Security

- Use WSS (WebSocket Secure) in production
- Validate WebSocket origin
- Implement rate limiting

## Monitoring & Debugging

### Key Metrics

- Active WebSocket connections
- Average call duration
- Audio conversion errors
- OpenAI API latency
- Connection drop rate

### Logging

All events logged:
```python
logger.info(f"Call {call_sid} connected")
logger.info(f"User said: {transcript}")
logger.info(f"AI response completed")
logger.error(f"Error: {error}")
```

### Debugging Tips

1. **Check WebSocket connection**:
   - Verify ngrok tunnel is active
   - Check BASE_URL in .env
   - Confirm port 3001 is accessible

2. **Audio issues**:
   - Check format conversion logs
   - Verify base64 encoding
   - Test with different audio samples

3. **OpenAI errors**:
   - Verify API key
   - Check model availability
   - Review session configuration

## Cost Optimization

### Reduce Audio Costs

1. **Use text fallback** for simple responses
2. **Implement silence detection** to pause streaming
3. **Cache common responses** (not feasible with real-time)
4. **Optimize conversation length** with better prompts

### Monitor Usage

```python
# Track audio duration
input_audio_seconds = total_input_frames * frame_duration
output_audio_seconds = total_output_frames * frame_duration

cost = (input_audio_seconds / 60 * 0.06) + \
       (output_audio_seconds / 60 * 0.24)
```

## Future Enhancements

1. **Function Calling**: Integrate with CRM during call
2. **Sentiment Analysis**: Detect user interest level
3. **Call Recording**: Store for quality assurance
4. **Multi-language**: Detect and switch languages
5. **Voice Cloning**: Custom brand voices
6. **Analytics Dashboard**: Real-time call monitoring

## References

- [OpenAI Realtime API Docs](https://platform.openai.com/docs/guides/realtime)
- [Twilio Media Streams](https://www.twilio.com/docs/voice/twiml/stream)
- [WebSocket RFC 6455](https://tools.ietf.org/html/rfc6455)
- [G.711 mulaw codec](https://en.wikipedia.org/wiki/G.711)

---

Last Updated: October 2024
