#!/bin/bash
# Setup script for Horizon AI Assistant Backend - macOS

echo "Setting up Horizon AI Assistant Backend for macOS..."

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Warning: This setup is optimized for macOS. You may need to use setup.sh for Linux."
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install system dependencies via Homebrew
echo "Installing system dependencies via Homebrew..."
brew update
brew install \
    tesseract \
    tesseract-lang \
    python@3.12 \
    pkg-config \
    cairo \
    gobject-introspection

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create config directory
echo "Creating config directory..."
mkdir -p ~/.horizon-ai/logs

# Set up macOS permissions info
echo ""
echo "⚠️  IMPORTANT: macOS Permission Setup Required"
echo "=============================================="
echo "For the Horizon AI Assistant to work properly on macOS, you need to:"
echo ""
echo "1. ACCESSIBILITY PERMISSIONS:"
echo "   - Go to System Preferences > Security & Privacy > Privacy > Accessibility"
echo "   - Add Terminal (or your terminal app) to the list"
echo "   - Add Python to the list when prompted"
echo ""
echo "2. SCREEN RECORDING PERMISSIONS:"
echo "   - Go to System Preferences > Security & Privacy > Privacy > Screen Recording"
echo "   - Add Terminal (or your terminal app) to the list"
echo "   - Add Python to the list when prompted"
echo ""
echo "3. INPUT MONITORING PERMISSIONS:"
echo "   - Go to System Preferences > Security & Privacy > Privacy > Input Monitoring"
echo "   - Add Terminal (or your terminal app) to the list"
echo ""
echo "These permissions are required for:"
echo "- Screen capture and OCR functionality"
echo "- Global hotkey detection"
echo "- System overlay display"
echo ""

# Test installations
echo "Testing installations..."

# Test Tesseract
if command -v tesseract &> /dev/null; then
    echo "✓ Tesseract OCR installed successfully"
    tesseract --version | head -1
else
    echo "⚠ Tesseract OCR installation may have failed"
fi

# Test Python imports
echo "Testing Python dependencies..."
python3 -c "
try:
    import fastapi
    print('✓ FastAPI installed')
except ImportError:
    print('⚠ FastAPI not installed')

try:
    import PyQt6
    print('✓ PyQt6 installed')
except ImportError:
    print('⚠ PyQt6 not installed')

try:
    import cv2
    print('✓ OpenCV installed')
except ImportError:
    print('⚠ OpenCV not installed')

try:
    import pytesseract
    print('✓ PyTesseract installed')
except ImportError:
    print('⚠ PyTesseract not installed')

try:
    from Cocoa import NSApplication
    print('✓ macOS Cocoa framework available')
except ImportError:
    print('⚠ macOS Cocoa framework not available')
"

echo ""
echo "Setup complete! To start the backend server:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the server: python main.py"
echo ""
echo "The backend will be available at http://localhost:8000"
echo "API documentation will be at http://localhost:8000/docs"
echo ""
echo "Remember to grant the required macOS permissions mentioned above!"