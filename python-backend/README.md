# Horizon AI Assistant - Python Backend

Python FastAPI backend for the Horizon AI Assistant, converted from Swift macOS application to support Ubuntu/Wayland.

## Overview

This backend provides the core functionality for the Horizon AI Assistant desktop application:

- **Global Hotkey Detection**: Using `evdev` for system-wide keyboard shortcuts
- **Screen Capture**: Using GNOME Shell D-Bus API for Wayland screenshots
- **OCR Processing**: Using `pytesseract` for text extraction from screenshots
- **Context Management**: Capturing selected text, browser URLs, and screen content
- **Overlay Management**: Coordinating with PyQt6 frontend for overlay display
- **Authentication**: User authentication and session management

## Architecture

### Core Components

```
python-backend/
├── main.py                 # FastAPI server entry point
├── requirements.txt        # Python dependencies
├── setup.sh               # Ubuntu setup script
│
├── services/              # Core business logic
│   ├── context_manager.py # Screen capture, OCR, text extraction
│   ├── input_manager.py   # Global hotkey detection (evdev)
│   ├── overlay_manager.py # Overlay state management
│   └── auth_manager.py    # Authentication management
│
├── api/                   # FastAPI routes
│   └── routes.py          # REST API endpoints
│
├── models/                # Data models
│   ├── context_data.py    # Context and note models
│   └── shortcut.py        # Keyboard shortcut model
│
└── utils/                 # Utilities
    ├── wayland_utils.py   # Wayland screen capture
    └── logging_config.py  # Logging configuration
```

## Key Features

### 1. Wayland Screen Capture
- Uses GNOME Shell Screenshot D-Bus API
- Fallback to `grim` for wlroots compositors
- PNG format with automatic cleanup

### 2. Global Hotkey Detection
- `evdev` for direct input device access
- Default shortcuts:
  - `Super+Shift+1`: AI Assist overlay
  - `Super+Shift+O`: Auto Context overlay
  - `Super+Shift+2`: Quick Capture overlay

### 3. Context Capture
- Selected text via clipboard (xclip)
- OCR text extraction from screenshots
- Browser URL detection from window titles
- Automatic context aggregation

### 4. API Endpoints

#### Health Check
```
GET / - Health check
GET /api/v1/health - Detailed health status
```

#### Context Management
```
POST /api/v1/context/capture - Capture current screen context
```

#### Overlay Control
```
POST /api/v1/overlay/ai-assist/toggle - Toggle AI Assist overlay
POST /api/v1/overlay/auto-context/toggle - Toggle Auto Context overlay
POST /api/v1/overlay/quick-capture/toggle - Toggle Quick Capture overlay
GET /api/v1/overlay/states - Get current overlay states
```

#### Authentication
```
POST /api/v1/auth/login - Authenticate user
POST /api/v1/auth/logout - Logout user
GET /api/v1/auth/status - Get auth status
```

#### Hotkey Management
```
GET /api/v1/hotkeys - Get current shortcuts
POST /api/v1/hotkeys/{action} - Update shortcut
```

### 5. WebSocket Communication
- Real-time communication with PyQt6 frontend
- Automatic overlay state broadcasting
- Context data streaming

## Setup and Installation

### Prerequisites
- Ubuntu 20.04+ with GNOME/Wayland
- Python 3.8+
- Root access for system dependencies

### Quick Setup
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Setup
```bash
# Install system dependencies
sudo apt install python3-dev python3-pip tesseract-ocr xclip xdotool libdbus-1-dev

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Add user to input group (for evdev)
sudo usermod -a -G input $USER
```

## Running the Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python main.py
```

The backend will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

## Configuration

### Logging
Logs are stored in `~/.horizon-ai/logs/horizon-ai.log`

### Authentication
Auth tokens are stored in `~/.horizon-ai/auth.json`

### Permissions
The user must be in the `input` group for hotkey detection:
```bash
sudo usermod -a -G input $USER
# Log out and back in for changes to take effect
```

## Ubuntu/Wayland Specific Features

### Screen Capture
- Primary: GNOME Shell D-Bus API
- Fallback: `grim` command (for wlroots)
- Automatic format conversion to PNG

### Input Detection
- Direct `evdev` device access
- Supports all keyboard devices
- Modifier key state tracking

### System Integration
- D-Bus session bus integration
- XDG desktop environment support
- Wayland compositor compatibility

## Development

### Adding New Endpoints
1. Add route to `api/routes.py`
2. Implement logic in appropriate service
3. Update models if needed

### Adding New Services
1. Create service in `services/`
2. Add to `HorizonApp` in `main.py`
3. Wire up initialization and cleanup

### Testing
```bash
# Run with auto-reload for development
python main.py

# Test API endpoints
curl http://localhost:8000/api/v1/health

# Test WebSocket
wscat -c ws://localhost:8000/ws
```

## Integration with PyQt6 Frontend

The backend communicates with the PyQt6 frontend via:
1. **REST API**: For configuration and one-time actions
2. **WebSocket**: For real-time overlay control and context updates

### WebSocket Message Format
```json
{
  "type": "overlay_action",
  "action": "toggle_ai_assist"
}
```

### Response Format
```json
{
  "success": true,
  "data": {
    "action": "show_ai_assist",
    "state": true,
    "context": { ... }
  }
}
```

## Troubleshooting

### Common Issues

1. **Permission Denied on /dev/input/***
   - Add user to input group: `sudo usermod -a -G input $USER`
   - Log out and back in

2. **Screenshot Capture Fails**
   - Ensure GNOME Shell is running
   - Check D-Bus permissions
   - Install `grim` as fallback

3. **OCR Not Working**
   - Install tesseract: `sudo apt install tesseract-ocr`
   - Install language packs: `sudo apt install tesseract-ocr-eng`

4. **Hotkeys Not Detected**
   - Check input group membership: `groups $USER`
   - Verify device permissions: `ls -la /dev/input/`
   - Check evdev device detection in logs

## Next Steps

This backend is ready for integration with the PyQt6 frontend. The frontend should:
1. Connect to WebSocket at `ws://localhost:8000/ws`
2. Listen for overlay toggle messages
3. Display appropriate overlay windows
4. Send context requests as needed