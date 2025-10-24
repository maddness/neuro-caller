# 🏗️ Architecture Documentation

## System Overview

Neuro-Caller is a voice-based AI recruitment system that combines Twilio's telephony platform with OpenAI's GPT-4 for natural language conversations.

## Architecture Diagram

```
┌─────────────┐
│   User's    │
│   Phone     │
└──────┬──────┘
       │
       │ (Phone Call)
       ▼
┌─────────────────────────────────────┐
│         Twilio Platform             │
│  ┌─────────────────────────────┐   │
│  │  Voice Call Management      │   │
│  │  - Speech-to-Text (STT)     │   │
│  │  - Text-to-Speech (TTS)     │   │
│  │  - Call Routing             │   │
│  └─────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │
               │ (Webhooks)
               ▼
┌──────────────────────────────────────┐
│       Flask Application              │
│  ┌────────────────────────────────┐  │
│  │    Voice Routes                │  │
│  │  - /voice/initial              │  │
│  │  - /voice/process              │  │
│  │  - /voice/status               │  │
│  └────────────────────────────────┘  │
│                                       │
│  ┌────────────────────────────────┐  │
│  │    Services Layer              │  │
│  │  ┌──────────────────────────┐  │  │
│  │  │  TwilioService           │  │  │
│  │  │  - make_call()           │  │  │
│  │  │  - create_response()     │  │  │
│  │  └──────────────────────────┘  │  │
│  │  ┌──────────────────────────┐  │  │
│  │  │  OpenAIService           │  │  │
│  │  │  - generate_response()   │  │  │
│  │  │  - manage_history()      │  │  │
│  │  └──────────────────────────┘  │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               │ (API Calls)
               ▼
┌──────────────────────────────────────┐
│         OpenAI Platform              │
│  ┌────────────────────────────────┐  │
│  │    GPT-4 API                   │  │
│  │  - Chat Completions            │  │
│  │  - Context Management          │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## Component Details

### 1. Twilio Platform

**Responsibilities:**
- Manage phone call lifecycle
- Convert speech to text (Russian language)
- Convert text to speech (Amazon Polly Tatyana voice)
- Send webhooks to Flask application

**Key Features:**
- Supports Russian phone numbers (+7)
- Real-time speech recognition
- Natural-sounding TTS with Polly
- Call status tracking

### 2. Flask Application

**Responsibilities:**
- Handle Twilio webhooks
- Orchestrate conversation flow
- Manage service integrations

**Endpoints:**

#### `/voice/initial` (POST)
- **Purpose**: Handle initial call connection
- **Input**: Twilio call parameters (CallSid, From, To)
- **Output**: TwiML with initial greeting
- **Flow**:
  1. Receive call connection event
  2. Generate initial greeting via OpenAI
  3. Return TwiML with greeting + speech gather

#### `/voice/process` (POST)
- **Purpose**: Process user speech and generate response
- **Input**: Twilio parameters + SpeechResult
- **Output**: TwiML with AI response
- **Flow**:
  1. Receive transcribed user speech
  2. Send to OpenAI with conversation context
  3. Get AI response
  4. Return TwiML with response + next gather

#### `/voice/status` (POST)
- **Purpose**: Track call status changes
- **Input**: Twilio call status updates
- **Output**: HTTP 200 OK
- **Flow**:
  1. Receive status update
  2. Log status change
  3. Clean up resources if call ended

### 3. OpenAIService

**Responsibilities:**
- Generate conversational responses
- Maintain conversation context
- Follow recruitment script logic

**Key Methods:**

#### `generate_response(user_message, call_sid)`
- Maintains per-call conversation history
- Uses GPT-4-turbo-preview model
- Temperature: 0.7 for natural variability
- Max tokens: 150 for concise responses

**Context Management:**
- Each call has isolated conversation history
- History stored in memory with call_sid as key
- Automatic cleanup on call end
- System prompt defines recruitment persona

**Prompt Engineering:**
```
Role: Friendly taxi service recruiter
Name: Анна
Brand: {TAXI_BRAND_NAME}

Instructions:
1. Speak naturally and concisely
2. Introduce yourself at start
3. Learn the person's name
4. Explain job benefits:
   - Flexible schedule
   - Weekly payments
   - Bonuses and rewards
   - 24/7 support
5. Answer questions
6. Offer to connect with manager if interested
7. Politely end call if declined
8. Always respond in Russian
9. Be friendly and professional
```

### 4. TwilioService

**Responsibilities:**
- Initiate outbound calls
- Generate TwiML responses
- Track call status

**Key Methods:**

#### `make_call(to_number)`
- Initiates outbound call
- Sets webhook URLs
- Returns call SID for tracking

#### `create_initial_response(greeting_text)`
- Generates TwiML for initial greeting
- Configures speech recognition (Russian)
- Sets timeout and language parameters

#### `create_conversation_response(ai_response)`
- Generates TwiML for AI response
- Detects end-of-conversation phrases
- Continues gather or hangs up accordingly

## Data Flow

### Outbound Call Flow

```
1. make_call.py
   └─> TwilioService.make_call(phone_number)
       └─> Twilio API: Create Call
           └─> Twilio calls webhook: /voice/initial
               └─> OpenAIService.generate_initial_greeting()
                   └─> Returns TwiML with greeting
                       └─> Twilio speaks greeting
                           └─> Waits for user speech

2. User speaks
   └─> Twilio STT: Speech → Text
       └─> Webhook: /voice/process with SpeechResult
           └─> OpenAIService.generate_response(speech)
               └─> OpenAI API: Generate response
                   └─> Returns TwiML with AI response
                       └─> Twilio speaks response
                           └─> Loop back to step 2

3. Call ends
   └─> Webhook: /voice/status with "completed"
       └─> OpenAIService.clear_history(call_sid)
           └─> Clean up conversation data
```

## State Management

### Conversation State
- **Storage**: In-memory dictionary
- **Key**: Twilio CallSid
- **Value**: List of messages (system, user, assistant)
- **Lifecycle**: Created on first message, deleted on call end

### Call State
- **Managed by**: Twilio
- **Statuses**: initiated, ringing, in-progress, completed, failed
- **Tracking**: Via /voice/status webhook

## Scalability Considerations

### Current Limitations
- In-memory conversation storage (not suitable for multi-instance)
- Synchronous request processing
- No call queueing

### Scaling Recommendations
1. **Conversation Storage**: Use Redis for shared state
2. **Request Processing**: Add async/await with asyncio
3. **Multiple Instances**: Load balancer + Redis session store
4. **Call Queueing**: Implement task queue (Celery/RQ)
5. **Monitoring**: Add APM (Application Performance Monitoring)

## Security Architecture

### API Key Management
- Environment variables (.env)
- Never committed to git
- Separate keys for dev/prod

### Webhook Security
- HTTPS required for production
- Validate Twilio signatures (TODO)
- Rate limiting (TODO)

### Data Privacy
- No call recordings stored
- Conversation history cleared after call
- Logs contain no PII

## Error Handling

### Network Errors
- Twilio: Automatic retries with exponential backoff
- OpenAI: Fallback to default message on API error

### Application Errors
- Try-catch blocks in all routes
- Logging to console
- Graceful error messages to caller

### Call Failures
- Busy/No-answer: Logged in status webhook
- Failed calls: Logged with error details

## Configuration

### Environment Variables
```
TWILIO_ACCOUNT_SID     - Twilio account identifier
TWILIO_AUTH_TOKEN      - Twilio authentication
TWILIO_PHONE_NUMBER    - Outbound caller ID
OPENAI_API_KEY         - OpenAI API access
PORT                   - Flask server port
BASE_URL               - Public webhook URL
TAXI_BRAND_NAME        - Brand name for prompts
RECRUITMENT_PROMPT     - Custom system prompt
```

### Runtime Configuration
- Located in `src/config.py`
- Validates required variables on startup
- Provides defaults for optional settings

## Monitoring & Logging

### Log Levels
- INFO: Normal operations (calls, responses)
- ERROR: Failures and exceptions
- DEBUG: Detailed flow (development only)

### Key Metrics to Track
- Call success rate
- Average call duration
- OpenAI API latency
- Error rates by type
- Cost per call

## Future Enhancements

1. **Database Integration**: Store call records and analytics
2. **Dashboard**: Web UI for monitoring and analytics
3. **A/B Testing**: Test different prompts and voices
4. **Callback Scheduling**: Allow users to schedule callbacks
5. **CRM Integration**: Sync interested leads to CRM
6. **Multi-language**: Support other languages
7. **Voice Cloning**: Custom brand voices
8. **Real-time Monitoring**: Live call dashboard

---

Last Updated: 2024
