"""
Permission Handler for Horizon Overlay.
Manages system permissions required for Ubuntu/Wayland operation.
"""

import asyncio
import subprocess
import os
import stat
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class PermissionLevel(Enum):
    """Permission requirement levels."""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"

@dataclass
class Permission:
    """System permission definition."""
    name: str
    description: str
    level: PermissionLevel
    check_method: str
    setup_method: Optional[str] = None
    setup_instructions: Optional[str] = None

class PermissionHandler:
    """Handles system permissions and access rights."""
    
    def __init__(self):
        self.permissions = {
            "input_devices": Permission(
                name="Input Device Access",
                description="Access to keyboard/mouse events for global hotkeys",
                level=PermissionLevel.REQUIRED,
                check_method="check_input_devices",
                setup_method="setup_input_devices",
                setup_instructions="Add user to input group and setup udev rules"
            ),
            "screenshot": Permission(
                name="Screenshot Access",
                description="Access to capture screen content via D-Bus",
                level=PermissionLevel.REQUIRED,
                check_method="check_screenshot_access",
                setup_instructions="Ensure GNOME Shell screenshot permission is granted"
            ),
            "clipboard": Permission(
                name="Clipboard Access",
                description="Access to system clipboard for text operations",
                level=PermissionLevel.REQUIRED,
                check_method="check_clipboard_access",
                setup_method="setup_clipboard_access"
            ),
            "notifications": Permission(
                name="Desktop Notifications",
                description="Send desktop notifications to user",
                level=PermissionLevel.RECOMMENDED,
                check_method="check_notification_access"
            ),
            "autostart": Permission(
                name="Autostart Permission",
                description="Start application automatically on login",
                level=PermissionLevel.OPTIONAL,
                check_method="check_autostart_permission",
                setup_method="setup_autostart"
            ),
            "system_tray": Permission(
                name="System Tray Access",
                description="Display system tray icon and menu",
                level=PermissionLevel.RECOMMENDED,
                check_method="check_system_tray_access"
            )
        }
        
        self.permission_status: Dict[str, bool] = {}
        self.setup_completed: Dict[str, bool] = {}
    
    async def check_all_permissions(self) -> Dict[str, bool]:
        """Check status of all permissions."""
        for perm_name, permission in self.permissions.items():
            try:
                check_method = getattr(self, permission.check_method)
                self.permission_status[perm_name] = await check_method()
            except Exception as e:
                print(f"Error checking permission {perm_name}: {e}")
                self.permission_status[perm_name] = False
        
        return self.permission_status.copy()
    
    async def check_input_devices(self) -> bool:
        """Check if user can access input devices."""
        try:
            # Check if user is in input group
            result = await asyncio.create_subprocess_exec(
                'groups',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                groups = stdout.decode().strip().split()
                if 'input' in groups:
                    # Also check if we can actually access input devices
                    input_devices = Path('/dev/input').glob('event*')
                    for device in input_devices:
                        if os.access(device, os.R_OK):
                            return True
            
            return False
            
        except Exception as e:
            print(f"Error checking input device access: {e}")
            return False
    
    async def setup_input_devices(self) -> bool:
        """Setup input device access."""
        try:
            print("Setting up input device access...")
            
            # Check if user is already in input group
            if await self.check_input_devices():
                print("Input device access already configured")
                return True
            
            # Instructions for manual setup
            setup_commands = [
                "# Add user to input group:",
                f"sudo usermod -a -G input {os.getenv('USER')}",
                "",
                "# Create udev rule for input access:",
                "sudo tee /etc/udev/rules.d/99-horizon-input.rules > /dev/null << 'EOF'",
                'KERNEL=="event*", GROUP="input", MODE="0664"',
                "EOF",
                "",
                "# Reload udev rules:",
                "sudo udevadm control --reload-rules",
                "sudo udevadm trigger",
                "",
                "# Log out and log back in for group changes to take effect"
            ]
            
            print("Input device setup requires manual configuration:")
            for cmd in setup_commands:
                print(cmd)
            
            print("\nAfter running these commands, log out and log back in.")
            return False  # Manual setup required
            
        except Exception as e:
            print(f"Error setting up input devices: {e}")
            return False
    
    async def check_screenshot_access(self) -> bool:
        """Check if we can capture screenshots."""
        try:
            # Test D-Bus screenshot access
            result = await asyncio.create_subprocess_exec(
                'gdbus', 'call', '--session',
                '--dest', 'org.gnome.Shell',
                '--object-path', '/org/gnome/Shell',
                '--method', 'org.gnome.Shell.Screenshot.Screenshot',
                'false', 'false', '"/tmp/horizon-test-screenshot.png"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            success = result.returncode == 0
            
            # Clean up test file
            test_file = Path("/tmp/horizon-test-screenshot.png")
            if test_file.exists():
                test_file.unlink()
            
            return success
            
        except Exception as e:
            print(f"Error checking screenshot access: {e}")
            return False
    
    async def check_clipboard_access(self) -> bool:
        """Check if we can access clipboard."""
        try:
            # Test xclip availability and access
            result = await asyncio.create_subprocess_exec(
                'which', 'xclip',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                # Test actual clipboard access
                test_result = await asyncio.create_subprocess_exec(
                    'xclip', '-version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await test_result.communicate()
                return test_result.returncode == 0
            
            return False
            
        except Exception as e:
            print(f"Error checking clipboard access: {e}")
            return False
    
    async def setup_clipboard_access(self) -> bool:
        """Setup clipboard access."""
        try:
            # Install xclip if not available
            if not await self.check_clipboard_access():
                print("Installing xclip for clipboard access...")
                
                result = await asyncio.create_subprocess_exec(
                    'sudo', 'apt', 'update', '&&',
                    'sudo', 'apt', 'install', '-y', 'xclip',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                return result.returncode == 0
            
            return True
            
        except Exception as e:
            print(f"Error setting up clipboard access: {e}")
            return False
    
    async def check_notification_access(self) -> bool:
        """Check if we can send notifications."""
        try:
            # Test notify-send availability
            result = await asyncio.create_subprocess_exec(
                'which', 'notify-send',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                # Test actual notification
                test_result = await asyncio.create_subprocess_exec(
                    'notify-send', '--urgency=low', '--expire-time=1',
                    'Horizon Permission Test', 'Testing notification access',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await test_result.communicate()
                return test_result.returncode == 0
            
            return False
            
        except Exception as e:
            print(f"Error checking notification access: {e}")
            return False
    
    async def check_autostart_permission(self) -> bool:
        """Check if autostart is configured."""
        try:
            autostart_dir = Path.home() / ".config/autostart"
            autostart_file = autostart_dir / "horizon-ai-assistant.desktop"
            
            return autostart_file.exists()
            
        except Exception as e:
            print(f"Error checking autostart permission: {e}")
            return False
    
    async def setup_autostart(self) -> bool:
        """Setup application autostart."""
        try:
            autostart_dir = Path.home() / ".config/autostart"
            autostart_dir.mkdir(exist_ok=True)
            
            autostart_file = autostart_dir / "horizon-ai-assistant.desktop"
            
            # Get current script path
            script_path = Path(__file__).parent.parent / "main.py"
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Horizon AI Assistant
Comment=AI-powered desktop overlay assistant
Icon=applications-science
Exec=python3 {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
"""
            
            with open(autostart_file, 'w') as f:
                f.write(desktop_content)
            
            # Make executable
            autostart_file.chmod(0o755)
            
            print(f"Autostart configured: {autostart_file}")
            return True
            
        except Exception as e:
            print(f"Error setting up autostart: {e}")
            return False
    
    async def check_system_tray_access(self) -> bool:
        """Check if system tray is available."""
        try:
            # Check for GNOME Shell
            gnome_result = await asyncio.create_subprocess_exec(
                'pgrep', '-x', 'gnome-shell',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await gnome_result.communicate()
            
            if gnome_result.returncode == 0:
                return True
            
            # Check for other system tray implementations
            tray_processes = ['unity-panel-service', 'xfce4-panel', 'lxpanel']
            for process in tray_processes:
                result = await asyncio.create_subprocess_exec(
                    'pgrep', '-x', process,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking system tray access: {e}")
            return False
    
    async def setup_required_permissions(self) -> Tuple[bool, List[str]]:
        """Setup all required permissions."""
        success = True
        failed_permissions = []
        
        for perm_name, permission in self.permissions.items():
            if permission.level == PermissionLevel.REQUIRED:
                if not self.permission_status.get(perm_name, False):
                    if permission.setup_method:
                        setup_method = getattr(self, permission.setup_method)
                        result = await setup_method()
                        self.setup_completed[perm_name] = result
                        
                        if not result:
                            success = False
                            failed_permissions.append(perm_name)
                    else:
                        success = False
                        failed_permissions.append(perm_name)
        
        return success, failed_permissions
    
    def get_permission_report(self) -> Dict[str, any]:
        """Get comprehensive permission status report."""
        report = {
            "permissions": {},
            "summary": {
                "total": len(self.permissions),
                "granted": 0,
                "required_missing": 0,
                "recommended_missing": 0,
                "optional_missing": 0
            }
        }
        
        for perm_name, permission in self.permissions.items():
            status = self.permission_status.get(perm_name, False)
            
            report["permissions"][perm_name] = {
                "name": permission.name,
                "description": permission.description,
                "level": permission.level.value,
                "granted": status,
                "setup_available": permission.setup_method is not None,
                "setup_completed": self.setup_completed.get(perm_name, False),
                "instructions": permission.setup_instructions
            }
            
            if status:
                report["summary"]["granted"] += 1
            else:
                if permission.level == PermissionLevel.REQUIRED:
                    report["summary"]["required_missing"] += 1
                elif permission.level == PermissionLevel.RECOMMENDED:
                    report["summary"]["recommended_missing"] += 1
                else:
                    report["summary"]["optional_missing"] += 1
        
        return report
    
    def print_permission_report(self):
        """Print human-readable permission report."""
        report = self.get_permission_report()
        
        print("\n" + "="*60)
        print("HORIZON AI ASSISTANT - PERMISSION REPORT")
        print("="*60)
        
        # Summary
        summary = report["summary"]
        print(f"\nSummary:")
        print(f"  ✓ Granted: {summary['granted']}/{summary['total']}")
        print(f"  ✗ Required missing: {summary['required_missing']}")
        print(f"  ⚠ Recommended missing: {summary['recommended_missing']}")
        print(f"  ○ Optional missing: {summary['optional_missing']}")
        
        # Detailed permissions
        print(f"\nDetailed Status:")
        for perm_name, perm_data in report["permissions"].items():
            status_icon = "✓" if perm_data["granted"] else "✗"
            level_icon = {
                "required": "🔴",
                "recommended": "🟡", 
                "optional": "🟢"
            }.get(perm_data["level"], "○")
            
            print(f"  {status_icon} {level_icon} {perm_data['name']}")
            print(f"      {perm_data['description']}")
            
            if not perm_data["granted"] and perm_data["instructions"]:
                print(f"      Setup: {perm_data['instructions']}")
            
            print()
        
        print("="*60)
    
    async def fix_permissions_interactive(self):
        """Interactive permission fixing process."""
        print("Starting interactive permission setup...")
        
        await self.check_all_permissions()
        
        # Show current status
        self.print_permission_report()
        
        # Fix required permissions
        required_missing = [
            perm_name for perm_name, permission in self.permissions.items()
            if (permission.level == PermissionLevel.REQUIRED and 
                not self.permission_status.get(perm_name, False))
        ]
        
        if required_missing:
            print(f"\nFound {len(required_missing)} missing required permissions.")
            print("Attempting automatic setup...")
            
            success, failed = await self.setup_required_permissions()
            
            if failed:
                print(f"\nAutomatic setup failed for: {', '.join(failed)}")
                print("Manual setup required. Please follow the instructions above.")
                return False
            else:
                print("✓ All required permissions configured successfully!")
                return True
        else:
            print("✓ All required permissions are already granted!")
            return True