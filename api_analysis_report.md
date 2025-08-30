# API Alignment Analysis Report

## Issues Identified

### 1. Missing Backend Client Methods
The frontend is calling methods that don't exist in the backend client:

**Frontend calls:**
- `backend_client.refresh_context()` - **MISSING**
- `backend_client.send_chat_message()` - **EXISTS** but different from backend API
- `backend_client.capture_context()` - **EXISTS** but parameters don't match

**Backend API endpoints:**
- `/api/v1/context/capture` - POST
- `/api/v1/context/search` - POST  
- `/api/v1/context/notes` - GET
- `/api/v1/ai/send-message` - POST

### 2. Parameter Mismatches

**Context Capture:**
- Frontend: `capture_context(include_screenshot: bool = False)`
- Backend: `capture_context(capture_image: bool = True)`

**AI Messages:**
- Frontend: `send_chat_message(message: str, context: Optional[Dict] = None)`
- Backend: `send_ai_message(text: str, smarter_analysis: bool = False)`

### 3. Response Format Inconsistencies

**Backend Response Format:**
```json
{
    "success": bool,
    "data": {...},
    "message": "..."
}
```

**Frontend Expected Format:**
```json
{
    "success": bool,
    "data": {...},
    "error": "..."
}
```

### 4. Missing API Endpoints

**Frontend expects but backend doesn't provide:**
- `/context/refresh` - for refreshing context
- `/ai/chat` - for chat messages (uses `/ai/send-message` instead)
- `/ai/chat/history` - for chat history (uses `/ai/messages` instead)
- `/notes` - for note management (uses `/context/notes` instead)

### 5. WebSocket Message Type Mismatches

**Frontend expects:**
- `context_changed`
- `selected_text`
- `window_focus`

**Backend sends:**
- Different message types through WebSocket

## Recommended Fixes

### 1. Add Missing Backend Client Methods
### 2. Align Parameter Names and Types
### 3. Standardize Response Formats
### 4. Add Missing Backend Endpoints
### 5. Fix WebSocket Message Types