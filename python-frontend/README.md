# Constella Horizon - Python Frontend

**An intelligent context-aware desktop overlay system for enhanced productivity and AI assistance**

---

## 🌟 Overview

Constella Horizon is a sophisticated desktop overlay application that provides intelligent context awareness, AI assistance, and seamless integration with your workflow. The Python frontend serves as the primary user interface and control system, designed to eventually replace the Swift implementation for cross-platform compatibility.

### Key Features

- **AI-Powered Assistance**: Real-time AI chat and assistance overlays
- **Context-Aware Capture**: Intelligent text and screen capture with automatic context detection
- **Smart Overlays**: Non-intrusive floating windows that adapt to your current work
- **Cross-Platform**: Built with Python/PyQt6 for Windows, macOS, and Linux support
- **Extensible Architecture**: Plugin-ready system for custom integrations
- **Real-time Collaboration**: WebSocket-based communication with backend services

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                 Python Frontend (UI Layer)              │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Overlays  │  │ System Tray │  │  Setup Wizard   │  │
│  │             │  │   Manager   │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                Service Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Backend    │  │  Capture    │  │   Input Event   │  │
│  │   Client    │  │  Service    │  │    Manager      │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────┤
│               Python Backend (API Layer)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ AI Services │  │  Data APIs  │  │  Authentication │  │
│  │             │  │             │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

### Core Application Files

```
python-frontend/
├── main.py                 # Application entry point and main controller
├── requirements.txt        # Python dependencies
└── run.py                 # Alternative entry point for development
```

### Configuration & Settings
```
config/
├── __init__.py
├── settings.py            # Application settings management
├── hotkeys.py            # Global hotkey configuration
└── themes.py             # UI theme management
```

### User Interface Components
```
ui/
├── overlays/             # Main overlay windows
│   ├── ai_assist.py      # AI chat and assistance overlay
│   ├── quick_capture.py  # Quick text/screen capture overlay
│   └── auto_context.py   # Automatic context detection overlay
├── setup/               # First-time setup wizard
│   ├── setup_wizard.py   # Main setup interface
│   ├── auth_setup.py     # Authentication configuration
│   └── preferences.py    # User preference setup
├── widgets/             # Reusable UI components
│   ├── floating_window.py # Base floating window class
│   ├── chat_widget.py    # AI chat interface widget
│   ├── capture_widget.py # Screen/text capture widget
│   └── context_widget.py # Context display widget
└── utils/               # UI utilities
    ├── window_manager.py # Window positioning and management
    ├── animations.py     # UI animations and transitions
    └── styling.py        # Custom styling and themes
```

### Core Services
```
services/
├── backend_client.py     # Communication with Python backend
├── overlay_manager.py    # Overlay window management
├── capture_service.py    # Screen and text capture functionality
├── input_manager.py      # Global hotkey and input handling
├── context_service.py    # Context detection and analysis
└── notification_service.py # System notifications
```

### System Integration
```
system/
├── platform/            # Platform-specific implementations
│   ├── windows.py        # Windows-specific features
│   ├── macos.py          # macOS-specific features
│   └── linux.py          # Linux-specific features
├── clipboard.py         # Clipboard management
├── screen_capture.py    # Screen capture utilities
└── hotkeys.py           # Global hotkey registration
```

### Data Models
```
models/
├── user.py              # User data models
├── context.py           # Context data structures
├── capture.py           # Capture session models
└── settings.py          # Settings data models
```

### Utilities
```
utils/
├── logger.py            # Logging configuration
├── encryption.py        # Data encryption utilities
├── file_manager.py      # File handling utilities
└── network.py           # Network utilities
```

---

## 🚀 Features in Detail

### 1. AI Assistant Overlay (`ui/overlays/ai_assist.py`)
- **Real-time AI Chat**: Floating chat window with context awareness
- **Smart Suggestions**: AI-powered suggestions based on current context
- **Multi-model Support**: Integration with various AI models
- **Context Integration**: Automatically includes relevant screen/text context

### 2. Quick Capture System (`ui/overlays/quick_capture.py`)
- **Text Capture**: Intelligent text selection and capture
- **Screen Capture**: Area/window/full screen capture with annotations
- **Automatic Processing**: AI-powered content analysis and tagging
- **Cloud Sync**: Automatic synchronization with backend storage

### 3. Auto Context Detection (`ui/overlays/auto_context.py`)
- **Smart Context Awareness**: Detects current application and content
- **Automatic Tagging**: AI-powered content categorization
- **Context History**: Maintains searchable context history
- **Privacy Controls**: User-configurable privacy and data handling

### 4. System Integration
- **Global Hotkeys**: System-wide keyboard shortcuts
- **System Tray**: Persistent system tray presence
- **Cross-platform**: Native integration on Windows, macOS, and Linux
- **Background Operation**: Minimal resource usage when not active

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.9+** (Recommended: Python 3.11)
- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Network**: Internet connection for AI features and sync

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd constella-horizon/python-frontend
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Platform-Specific Setup**
   
   **Windows:**
   ```bash
   # Install Windows-specific dependencies
   pip install pywin32 pycryptodome
   ```
   
   **macOS:**
   ```bash
   # Install macOS-specific dependencies
   pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz
   ```
   
   **Linux:**
   ```bash
   # Install Linux-specific dependencies (Ubuntu/Debian)
   sudo apt-get install python3-dev libxtst6 libxss1
   pip install python-xlib pycryptodome
   ```

5. **Configuration**
   ```bash
   # Copy default configuration
   cp config/settings.default.json config/settings.json
   
   # Edit configuration as needed
   nano config/settings.json
   ```

6. **First Run**
   ```bash
   python main.py
   ```

   The application will launch the setup wizard on first run to configure:
   - Authentication settings
   - AI service connections
   - Hotkey preferences
   - Privacy settings

---

## 📖 User Guide

### Getting Started

1. **Initial Setup**
   - Run the application for the first time
   - Complete the setup wizard
   - Configure your preferred hotkeys
   - Set up AI service connections

2. **Basic Operations**
   - **Access System Tray**: Right-click the Constella Horizon icon
   - **AI Assist**: Use configured hotkey (default: `Ctrl+Shift+A`)
   - **Quick Capture**: Use configured hotkey (default: `Ctrl+Shift+C`)
   - **Auto Context**: Automatically activated based on settings

### Core Workflows

#### AI Assistance Workflow
1. Trigger AI Assist overlay with hotkey
2. Type your question or request
3. AI responds with context-aware assistance
4. Copy responses or continue conversation
5. Close overlay or minimize to continue working

#### Quick Capture Workflow
1. Trigger Quick Capture with hotkey
2. Select capture type (text/screen/area)
3. Make selection or capture
4. AI automatically analyzes and tags content
5. Content is saved and synchronized

#### Context Management
1. Auto Context runs in background
2. Monitors current application and content
3. Builds searchable context history
4. Provides relevant suggestions
5. Maintains privacy controls

### Hotkey Configuration

Default hotkeys can be customized in settings:

| Function | Default Hotkey | Customizable |
|----------|----------------|--------------|
| AI Assist | `Ctrl+Shift+A` | ✅ |
| Quick Capture | `Ctrl+Shift+C` | ✅ |
| Context Toggle | `Ctrl+Shift+X` | ✅ |
| Settings | `Ctrl+Shift+S` | ✅ |

### Settings Management

Access settings through:
- System tray menu → Settings
- AI Assist overlay → Settings icon
- Hotkey: `Ctrl+Shift+S`

Key settings categories:
- **General**: Basic application preferences
- **AI Services**: AI model configuration and API keys
- **Privacy**: Data handling and privacy controls
- **Hotkeys**: Global shortcut customization
- **Appearance**: UI themes and display options

---

## 🔧 Development Guide

### Development Setup

1. **Development Dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Code Quality Tools**
   ```bash
   # Linting
   flake8 .
   
   # Type checking
   mypy .
   
   # Code formatting
   black .
   ```

3. **Testing**
   ```bash
   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=. --cov-report=html
   ```

### Architecture Patterns

- **MVC Pattern**: Models, Views, and Controllers clearly separated
- **Observer Pattern**: Event-driven communication between components
- **Factory Pattern**: Dynamic creation of overlay windows and services
- **Singleton Pattern**: Global managers (settings, overlay manager)

### Adding New Features

1. **New Overlay Window**
   ```python
   # Create in ui/overlays/
   class NewOverlay(FloatingWindow):
       def __init__(self, parent=None):
           super().__init__(parent)
           self.setup_ui()
       
       def setup_ui(self):
           # Implement UI setup
           pass
   ```

2. **New Service**
   ```python
   # Create in services/
   class NewService:
       def __init__(self, settings):
           self.settings = settings
       
       async def start(self):
           # Implement service startup
           pass
   ```

3. **Platform-Specific Code**
   ```python
   # Add to system/platform/
   class WindowsPlatform:
       @staticmethod
       def get_active_window():
           # Windows-specific implementation
           pass
   ```

### Code Style Guidelines

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Document all classes and public methods
- **Error Handling**: Implement comprehensive error handling
- **Logging**: Use structured logging throughout

---

## 🔌 API Integration

### Backend Communication

The frontend communicates with the Python backend via:

- **REST API**: For data operations and configuration
- **WebSockets**: For real-time features and AI interactions
- **gRPC**: For high-performance operations (optional)

### AI Service Integration

Supported AI services:
- **OpenAI GPT Models**: GPT-3.5, GPT-4, and newer
- **Anthropic Claude**: Claude-3 and newer models
- **Local Models**: Ollama and other local inference engines
- **Custom APIs**: Configurable custom AI endpoints

### External Integrations

- **Cloud Storage**: Google Drive, Dropbox, OneDrive
- **Note-taking Apps**: Notion, Obsidian, Roam Research
- **Productivity Tools**: Slack, Discord, email clients
- **Development Tools**: VS Code, JetBrains IDEs

---

## 🚨 Troubleshooting

### Common Issues

1. **Application Won't Start**
   - Check Python version (3.9+ required)
   - Verify all dependencies installed
   - Check log files in `logs/` directory

2. **Hotkeys Not Working**
   - Verify hotkeys not conflicting with other applications
   - Run application as administrator (Windows) or with accessibility permissions (macOS)
   - Check system/hotkeys.py for platform-specific issues

3. **AI Features Not Responding**
   - Verify internet connection
   - Check AI service API keys in settings
   - Review backend connectivity in logs

4. **Overlay Windows Not Appearing**
   - Check display configuration and multi-monitor setup
   - Verify window manager compatibility (Linux)
   - Review overlay positioning settings

### Debug Mode

Enable debug mode for troubleshooting:
```bash
python main.py --debug
```

This enables:
- Verbose logging
- Developer console access
- Enhanced error reporting
- Performance monitoring

### Log Files

Log files are stored in:
- **Windows**: `%APPDATA%/ConstellaHorizon/logs/`
- **macOS**: `~/Library/Logs/ConstellaHorizon/`
- **Linux**: `~/.local/share/ConstellaHorizon/logs/`

---

## 🛣️ Future Roadmap

### Phase 1: Swift Replacement (Current)
- ✅ Core overlay functionality
- ✅ System tray integration
- ✅ Basic AI assistance
- 🔄 Feature parity with Swift version
- 🔄 Cross-platform stability

### Phase 2: Enhanced Features
- 📋 Advanced context analysis
- 📋 Plugin system architecture
- 📋 Enhanced AI model support
- 📋 Improved performance optimization
- 📋 Advanced customization options

### Phase 3: Ecosystem Expansion
- 📋 Mobile companion apps
- 📋 Web interface
- 📋 Enterprise features
- 📋 Advanced collaboration tools
- 📋 Marketplace for plugins

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- Code style and standards
- Pull request process
- Issue reporting
- Feature requests
- Documentation improvements

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Run code quality checks
5. Submit pull request with description

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support

- **Documentation**: Full documentation available in `/docs`
- **Issues**: Report bugs and request features via GitHub Issues
- **Community**: Join our Discord community for support and discussions
- **Email**: Contact support@constellahorizon.com for enterprise inquiries

---

**Note**: This Python frontend is designed to completely replace the Swift implementation, providing cross-platform compatibility and enhanced features while maintaining the same user experience and functionality.