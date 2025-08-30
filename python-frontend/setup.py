#!/bin/bash
"""
Setup script for Horizon Overlay Python Frontend
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"➤ {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    if sys.version_info < (3.8, 0):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def install_system_dependencies():
    """Install system dependencies for Linux"""
    print("\n📦 Installing system dependencies...")
    
    # Detect package manager
    if os.path.exists("/usr/bin/apt"):
        # Debian/Ubuntu
        commands = [
            "sudo apt update",
            "sudo apt install -y python3-dev python3-pip python3-venv",
            "sudo apt install -y libportaudio2 libportaudio-dev",
            "sudo apt install -y python3-pyqt6 python3-pyqt6.qtmultimedia",
            "sudo apt install -y libdbus-1-dev libdbus-glib-1-dev",
            "sudo apt install -y xdotool imagemagick scrot maim",
            "sudo apt install -y libasound2-dev"
        ]
    elif os.path.exists("/usr/bin/dnf"):
        # Fedora
        commands = [
            "sudo dnf install -y python3-devel python3-pip",
            "sudo dnf install -y portaudio-devel",
            "sudo dnf install -y python3-qt6 python3-qt6-multimedia",
            "sudo dnf install -y dbus-devel dbus-glib-devel",
            "sudo dnf install -y xdotool ImageMagick scrot",
            "sudo dnf install -y alsa-lib-devel"
        ]
    elif os.path.exists("/usr/bin/pacman"):
        # Arch Linux
        commands = [
            "sudo pacman -Sy --noconfirm python python-pip",
            "sudo pacman -S --noconfirm portaudio",
            "sudo pacman -S --noconfirm python-pyqt6",
            "sudo pacman -S --noconfirm dbus-glib",
            "sudo pacman -S --noconfirm xdotool imagemagick scrot maim",
            "sudo pacman -S --noconfirm alsa-lib"
        ]
    else:
        print("⚠️  Unknown package manager. Please install dependencies manually:")
        print("- Python 3.8+ development packages")
        print("- PortAudio development libraries")
        print("- PyQt6")
        print("- D-Bus development libraries")
        print("- xdotool, ImageMagick, scrot, maim")
        print("- ALSA development libraries")
        return True
    
    for cmd in commands:
        if not run_command(cmd, f"Running: {cmd}"):
            print(f"⚠️  Failed to run: {cmd}")
            print("You may need to install dependencies manually")
    
    return True


def create_virtual_environment():
    """Create Python virtual environment"""
    print("\n🐍 Creating Python virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✓ Virtual environment already exists")
        return True
    
    return run_command("python3 -m venv venv", "Creating virtual environment")


def install_python_dependencies():
    """Install Python dependencies"""
    print("\n📚 Installing Python dependencies...")
    
    pip_cmd = "./venv/bin/pip" if os.name != 'nt' else "venv\\Scripts\\pip.exe"
    
    # Upgrade pip first
    run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip")
    
    # Install dependencies
    dependencies = [
        "PyQt6>=6.4.0",
        "qasync>=0.24.0",
        "evdev>=1.6.0",
        "pydbus>=0.6.0", 
        "sounddevice>=0.4.5",
        "numpy>=1.21.0",
        "aiohttp>=3.8.0",
        "websockets>=10.4",
        "Pillow>=9.0.0",
        "pydantic>=1.10.0",
        "toml>=0.10.0"
    ]
    
    for dep in dependencies:
        if not run_command(f"{pip_cmd} install {dep}", f"Installing {dep}"):
            print(f"⚠️  Failed to install {dep}")
    
    return True


def create_desktop_entry():
    """Create desktop entry for the application"""
    print("\n🖥️  Creating desktop entry...")
    
    desktop_content = f"""[Desktop Entry]
Name=Horizon Overlay
Comment=AI-powered overlay for enhanced productivity
Exec={Path.cwd()}/run.sh
Icon={Path.cwd()}/assets/icons/app_icon.png
Terminal=false
Type=Application
Categories=Utility;Productivity;
StartupNotify=true
"""
    
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    
    desktop_file = desktop_dir / "horizon-overlay.desktop"
    try:
        desktop_file.write_text(desktop_content)
        os.chmod(desktop_file, 0o755)
        print(f"✓ Desktop entry created: {desktop_file}")
        return True
    except Exception as e:
        print(f"⚠️  Failed to create desktop entry: {e}")
        return False


def create_run_script():
    """Create run script"""
    print("\n📜 Creating run script...")
    
    run_script_content = f"""#!/bin/bash
cd "{Path.cwd()}"
source venv/bin/activate
python main.py "$@"
"""
    
    run_script = Path("run.sh")
    try:
        run_script.write_text(run_script_content)
        os.chmod(run_script, 0o755)
        print("✓ Run script created: run.sh")
        return True
    except Exception as e:
        print(f"⚠️  Failed to create run script: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        "assets/icons",
        "logs",
        "config/user"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")


def main():
    """Main setup function"""
    print("🚀 Setting up Horizon Overlay Python Frontend")
    print("=" * 50)
    
    check_python_version()
    install_system_dependencies()
    create_virtual_environment()
    install_python_dependencies()
    create_directories()
    create_run_script()
    create_desktop_entry()
    
    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nTo run the application:")
    print("  ./run.sh")
    print("\nOr manually:")
    print("  source venv/bin/activate")
    print("  python main.py")


if __name__ == "__main__":
    main()