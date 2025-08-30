"""
FastAPI routes - Main API endpoints for Horizon AI Assistant
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import asyncio

from services.overlay_manager import OverlayManager
from services.context_manager import AIContextManager
from services.auth_manager import AuthManager
from services.input_manager import InputManager
from ai.connection_manager import AIConnectionManager
from ai.tag_websocket_manager import TagWebSocketManager
from api.context_search import AutoContextManager, SearchMethod
from models.context_data import ContextData
from models.shortcut import Shortcut

api_router = APIRouter()

# Dependency injection for managers
def get_overlay_manager() -> OverlayManager:
    from main import horizon_app
    return horizon_app.overlay_manager

def get_context_manager() -> AIContextManager:
    from main import horizon_app
    return horizon_app.context_manager

def get_auth_manager() -> AuthManager:
    from main import horizon_app
    return horizon_app.auth_manager

def get_input_manager() -> InputManager:
    from main import horizon_app
    return horizon_app.input_manager

def get_ai_connection_manager() -> AIConnectionManager:
    from main import horizon_app
    return horizon_app.ai_connection_manager

def get_tag_websocket_manager() -> TagWebSocketManager:
    from main import horizon_app
    return horizon_app.tag_websocket_manager

def get_auto_context_manager() -> AutoContextManager:
    from main import horizon_app
    return horizon_app.auto_context_manager


@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "horizon-ai-backend"}


# Context API endpoints
@api_router.post("/context/capture")
async def capture_context(
    capture_image: bool = True,
    context_manager: AIContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """Capture current screen context"""
    try:
        context_data = await context_manager.capture_current_context(capture_image=capture_image)
        
        return {
            "success": True,
            "data": {
                "selected_text": context_data.selected_text,
                "ocr_text": context_data.ocr_text,
                "browser_url": context_data.browser_url,
                "has_image": context_data.image_data is not None,
                "timestamp": context_data.timestamp.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/context/search")
async def search_context(
    ocr_text: str,
    method: str = "sentence_chunks",
    auto_context_manager: AutoContextManager = Depends(get_auto_context_manager)
) -> Dict[str, Any]:
    """Search for context based on OCR text"""
    try:
        search_method = SearchMethod.SENTENCE_CHUNKS if method == "sentence_chunks" else SearchMethod.TOPIC_EXTRACTION
        
        # Connect if not already connected
        if not auto_context_manager.context_search_api.is_connected:
            await auto_context_manager.connect(search_method)
        
        # Perform search
        await auto_context_manager.search_context(ocr_text)
        
        return {
            "success": True,
            "message": "Context search initiated",
            "search_method": method
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/context/notes")
async def get_context_notes(
    auto_context_manager: AutoContextManager = Depends(get_auto_context_manager)
) -> Dict[str, Any]:
    """Get current context notes"""
    try:
        notes_data = []
        for note in auto_context_manager.context_notes:
            notes_data.append({
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
                "uniqueid": note.uniqueid
            })
        
        return {
            "success": True,
            "data": {
                "notes": notes_data,
                "count": len(notes_data),
                "is_loading": auto_context_manager.is_loading
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI Chat endpoints
@api_router.post("/ai/send-message")
async def send_ai_message(
    text: str,
    smarter_analysis: bool = False,
    ai_manager: AIConnectionManager = Depends(get_ai_connection_manager),
    context_manager: AIContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """Send message to AI with current context"""
    try:
        # Capture current context
        context_data = await context_manager.capture_current_context(capture_image=True)
        
        # Send to AI
        await ai_manager.send_message(
            text=text,
            ocr_text=context_data.ocr_text,
            selected_text=context_data.selected_text,
            browser_url=context_data.browser_url,
            image_data=context_data.image_data,
            smarter_analysis_enabled=smarter_analysis
        )
        
        return {
            "success": True,
            "message": "AI message sent successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/ai/status")
async def get_ai_status(
    ai_manager: AIConnectionManager = Depends(get_ai_connection_manager)
) -> Dict[str, Any]:
    """Get AI connection status"""
    status = ai_manager.get_connection_status()
    
    return {
        "success": True,
        "data": {
            "connected": status["connected"],
            "receiving": status["receiving"],
            "message_count": status["message_count"],
            "reconnection_attempts": status["reconnection_attempts"]
        }
    }


@api_router.get("/ai/messages")
async def get_ai_messages(
    ai_manager: AIConnectionManager = Depends(get_ai_connection_manager)
) -> Dict[str, Any]:
    """Get AI message history"""
    try:
        messages_data = []
        for msg in ai_manager.last_messages:
            messages_data.append({
                "id": msg.id,
                "message": msg.message,
                "is_user": msg.is_user,
                "timestamp": msg.timestamp.isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "messages": messages_data,
                "current_stream": ai_manager.message_stream,
                "is_receiving": ai_manager.is_receiving
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/ai/clear-conversation")
async def clear_ai_conversation(
    ai_manager: AIConnectionManager = Depends(get_ai_connection_manager)
) -> Dict[str, Any]:
    """Clear AI conversation history"""
    try:
        ai_manager.clear_conversation()
        return {
            "success": True,
            "message": "Conversation cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Tag management endpoints
@api_router.get("/tags")
async def get_all_tags(
    tag_manager: TagWebSocketManager = Depends(get_tag_websocket_manager)
) -> Dict[str, Any]:
    """Get all tags"""
    try:
        tags_data = []
        for tag in tag_manager.tags:
            tags_data.append({
                "id": tag.id,
                "name": tag.name,
                "color": tag.color
            })
        
        return {
            "success": True,
            "data": {
                "tags": tags_data,
                "count": len(tags_data),
                "is_loading": tag_manager.is_loading,
                "is_connected": tag_manager.is_connected
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/tags/search")
async def search_tags(
    query: str,
    tag_manager: TagWebSocketManager = Depends(get_tag_websocket_manager)
) -> Dict[str, Any]:
    """Search tags by name"""
    try:
        matching_tags = tag_manager.get_tags_containing(query)
        
        tags_data = []
        for tag in matching_tags:
            tags_data.append({
                "id": tag.id,
                "name": tag.name,
                "color": tag.color
            })
        
        return {
            "success": True,
            "data": {
                "tags": tags_data,
                "count": len(tags_data),
                "query": query
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/tags/{tag_id}")
async def get_tag(
    tag_id: str,
    tag_manager: TagWebSocketManager = Depends(get_tag_websocket_manager)
) -> Dict[str, Any]:
    """Get specific tag by ID"""
    try:
        tag = tag_manager.get_tag(tag_id)
        
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        return {
            "success": True,
            "data": {
                "id": tag.id,
                "name": tag.name,
                "color": tag.color
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/tags/refresh")
async def refresh_tags(
    tag_manager: TagWebSocketManager = Depends(get_tag_websocket_manager)
) -> Dict[str, Any]:
    """Refresh tags from server"""
    try:
        await tag_manager.refresh_tags()
        return {
            "success": True,
            "message": "Tags refreshed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/tags/status")
async def get_tag_status(
    tag_manager: TagWebSocketManager = Depends(get_tag_websocket_manager)
) -> Dict[str, Any]:
    """Get tag manager status"""
    return {
        "success": True,
        "data": {
            "connected": tag_manager.is_connected,
            "loading": tag_manager.is_loading,
            "error": tag_manager.error,
            "tag_count": len(tag_manager.tags),
            "tenant_name": tag_manager.tenant_name,
            "reconnection_attempts": tag_manager.reconnection_attempts
        }
    }


# Overlay API endpoints
@api_router.post("/overlay/ai-assist/toggle")
async def toggle_ai_assist(
    overlay_manager: OverlayManager = Depends(get_overlay_manager)
) -> Dict[str, Any]:
    """Toggle AI Assist overlay"""
    try:
        result = await overlay_manager.toggle_ai_assist()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/overlay/auto-context/toggle")
async def toggle_auto_context(
    overlay_manager: OverlayManager = Depends(get_overlay_manager)
) -> Dict[str, Any]:
    """Toggle Auto Context overlay"""
    try:
        result = await overlay_manager.toggle_auto_context()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/overlay/quick-capture/toggle")
async def toggle_quick_capture(
    overlay_manager: OverlayManager = Depends(get_overlay_manager)
) -> Dict[str, Any]:
    """Toggle Quick Capture overlay"""
    try:
        result = await overlay_manager.toggle_quick_capture()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/overlay/states")
async def get_overlay_states(
    overlay_manager: OverlayManager = Depends(get_overlay_manager)
) -> Dict[str, Any]:
    """Get current overlay states"""
    return {
        "success": True,
        "data": overlay_manager.overlay_states
    }


# Authentication endpoints
@api_router.post("/auth/login")
async def login(
    token: str,
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """Authenticate user"""
    try:
        success = await auth_manager.authenticate(token)
        
        return {
            "success": success,
            "data": {
                "authenticated": auth_manager.is_authenticated,
                "user_data": auth_manager.user_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/auth/logout")
async def logout(
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """Logout user"""
    try:
        await auth_manager.logout()
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/auth/status")
async def auth_status(
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> Dict[str, Any]:
    """Get authentication status"""
    return {
        "success": True,
        "data": {
            "authenticated": auth_manager.is_authenticated,
            "user_data": auth_manager.user_data,
            "tenant_name": auth_manager.get_tenant_name()
        }
    }


# Hotkey management endpoints
@api_router.get("/hotkeys")
async def get_hotkeys(
    input_manager: InputManager = Depends(get_input_manager)
) -> Dict[str, Any]:
    """Get current hotkey shortcuts"""
    shortcuts = {}
    for action in ['aiAssist', 'autoContext', 'quickCapture']:
        shortcut = input_manager.get_shortcut(action)
        if shortcut:
            shortcuts[action] = {
                "key": shortcut.key,
                "modifiers": shortcut.modifiers,
                "display": str(shortcut)
            }
    
    return {"success": True, "data": shortcuts}


@api_router.post("/hotkeys/{action}")
async def update_hotkey(
    action: str,
    key: str,
    modifiers: list,
    input_manager: InputManager = Depends(get_input_manager)
) -> Dict[str, Any]:
    """Update hotkey shortcut for an action"""
    try:
        if action not in ['aiAssist', 'autoContext', 'quickCapture']:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        shortcut = Shortcut(key=key, modifiers=modifiers)
        input_manager.update_shortcut(action, shortcut)
        
        return {
            "success": True,
            "message": f"Updated {action} shortcut to {shortcut}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# System status endpoint
@api_router.get("/system/status")
async def get_system_status(
    auth_manager: AuthManager = Depends(get_auth_manager),
    ai_manager: AIConnectionManager = Depends(get_ai_connection_manager),
    tag_manager: TagWebSocketManager = Depends(get_tag_websocket_manager),
    auto_context_manager: AutoContextManager = Depends(get_auto_context_manager)
) -> Dict[str, Any]:
    """Get comprehensive system status"""
    return {
        "success": True,
        "data": {
            "authentication": {
                "authenticated": auth_manager.is_authenticated,
                "tenant_name": auth_manager.get_tenant_name()
            },
            "ai_connection": {
                "connected": ai_manager.is_connected,
                "receiving": ai_manager.is_receiving,
                "message_count": len(ai_manager.message_history)
            },
            "tag_manager": {
                "connected": tag_manager.is_connected,
                "tag_count": len(tag_manager.tags),
                "loading": tag_manager.is_loading
            },
            "context_search": {
                "connected": auto_context_manager.context_search_api.is_connected,
                "note_count": len(auto_context_manager.context_notes),
                "loading": auto_context_manager.is_loading
            }
        }
    }