"""
Notification Manager for Horizon Overlay.
Handles desktop notifications for Ubuntu/GNOME.
"""

import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
import json
import time

class NotificationUrgency(Enum):
    """Notification urgency levels."""
    LOW = "low"
    NORMAL = "normal" 
    CRITICAL = "critical"

class NotificationCategory(Enum):
    """Notification categories."""
    AI_RESPONSE = "ai.response"
    CONTEXT_UPDATE = "context.update"
    ERROR = "error"
    INFO = "info"
    OVERLAY_STATUS = "overlay.status"

@dataclass
class NotificationAction:
    """Notification action button."""
    id: str
    label: str
    callback: Optional[callable] = None

@dataclass
class HorizonNotification:
    """Notification data structure."""
    title: str
    message: str
    urgency: NotificationUrgency = NotificationUrgency.NORMAL
    category: NotificationCategory = NotificationCategory.INFO
    timeout: int = 5000  # milliseconds
    icon: Optional[str] = None
    actions: List[NotificationAction] = None
    replace_id: Optional[int] = None

class NotificationManager:
    """Desktop notification manager for GNOME/Ubuntu."""
    
    def __init__(self):
        self.app_name = "Horizon AI Assistant"
        self.app_icon = "applications-science"
        self.notifications_enabled = True
        self.active_notifications: Dict[int, HorizonNotification] = {}
        self.notification_counter = 0
        
        # Notification history for debugging
        self.notification_history: List[Dict[str, Any]] = []
        
    async def setup(self) -> bool:
        """Setup notification system."""
        try:
            # Check if notification daemon is available
            if await self._check_notification_support():
                await self._register_application()
                print("Notification manager initialized successfully")
                return True
            else:
                print("No notification daemon found")
                return False
        except Exception as e:
            print(f"Failed to setup notifications: {e}")
            return False
    
    async def _check_notification_support(self) -> bool:
        """Check if desktop notifications are supported."""
        try:
            # Test basic notify-send availability
            result = await asyncio.create_subprocess_exec(
                'which', 'notify-send',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                # Test if we can actually send a notification
                test_result = await asyncio.create_subprocess_exec(
                    'notify-send', '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await test_result.communicate()
                return test_result.returncode == 0
            
            return False
            
        except Exception as e:
            print(f"Error checking notification support: {e}")
            return False
    
    async def _register_application(self):
        """Register application with notification daemon."""
        try:
            # Send a silent registration notification
            await asyncio.create_subprocess_exec(
                'notify-send',
                '--app-name', self.app_name,
                '--icon', self.app_icon,
                '--urgency', 'low',
                '--expire-time', '1',
                'Horizon AI Assistant',
                'Desktop notifications enabled',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            print(f"Failed to register with notification daemon: {e}")
    
    async def send_notification(self, notification: HorizonNotification) -> Optional[int]:
        """
        Send a desktop notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            Optional[int]: Notification ID if successful
        """
        if not self.notifications_enabled:
            return None
        
        try:
            self.notification_counter += 1
            notification_id = self.notification_counter
            
            # Build notify-send command
            cmd = [
                'notify-send',
                '--app-name', self.app_name,
                '--urgency', notification.urgency.value,
                '--expire-time', str(notification.timeout),
                '--category', notification.category.value
            ]
            
            # Add icon if specified
            if notification.icon:
                cmd.extend(['--icon', notification.icon])
            else:
                cmd.extend(['--icon', self.app_icon])
            
            # Add replace ID if specified (for updating existing notifications)
            if notification.replace_id:
                cmd.extend(['--replace-id', str(notification.replace_id)])
            
            # Add actions if supported
            if notification.actions:
                for action in notification.actions:
                    cmd.extend(['--action', f"{action.id}={action.label}"])
            
            # Add title and message
            cmd.extend([notification.title, notification.message])
            
            # Send notification
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Store notification
                self.active_notifications[notification_id] = notification
                
                # Add to history
                self.notification_history.append({
                    'id': notification_id,
                    'title': notification.title,
                    'message': notification.message,
                    'timestamp': time.time(),
                    'category': notification.category.value,
                    'urgency': notification.urgency.value
                })
                
                # Limit history size
                if len(self.notification_history) > 100:
                    self.notification_history = self.notification_history[-50:]
                
                print(f"Notification sent: {notification.title}")
                return notification_id
            else:
                print(f"Failed to send notification: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Error sending notification: {e}")
            return None
    
    async def send_ai_response_notification(self, message: str, preview: str = None) -> Optional[int]:
        """Send notification for AI response."""
        preview_text = preview or (message[:100] + "..." if len(message) > 100 else message)
        
        notification = HorizonNotification(
            title="AI Assistant Response",
            message=preview_text,
            category=NotificationCategory.AI_RESPONSE,
            urgency=NotificationUrgency.NORMAL,
            timeout=8000,
            actions=[
                NotificationAction("view", "View Full Response"),
                NotificationAction("copy", "Copy to Clipboard")
            ]
        )
        
        return await self.send_notification(notification)
    
    async def send_context_update_notification(self, context_type: str, count: int) -> Optional[int]:
        """Send notification for context updates."""
        notification = HorizonNotification(
            title="Context Updated",
            message=f"Found {count} relevant {context_type} items",
            category=NotificationCategory.CONTEXT_UPDATE,
            urgency=NotificationUrgency.LOW,
            timeout=4000
        )
        
        return await self.send_notification(notification)
    
    async def send_error_notification(self, error_title: str, error_message: str) -> Optional[int]:
        """Send error notification."""
        notification = HorizonNotification(
            title=error_title,
            message=error_message,
            category=NotificationCategory.ERROR,
            urgency=NotificationUrgency.CRITICAL,
            timeout=10000,
            icon="dialog-error"
        )
        
        return await self.send_notification(notification)
    
    async def send_overlay_status_notification(self, overlay_name: str, is_active: bool) -> Optional[int]:
        """Send overlay status notification."""
        status = "activated" if is_active else "deactivated"
        
        notification = HorizonNotification(
            title=f"{overlay_name} {status.title()}",
            message=f"{overlay_name} overlay has been {status}",
            category=NotificationCategory.OVERLAY_STATUS,
            urgency=NotificationUrgency.LOW,
            timeout=3000
        )
        
        return await self.send_notification(notification)
    
    async def send_quick_notification(self, title: str, message: str, 
                                    urgency: NotificationUrgency = NotificationUrgency.NORMAL) -> Optional[int]:
        """Send a quick notification with minimal configuration."""
        notification = HorizonNotification(
            title=title,
            message=message,
            urgency=urgency,
            timeout=5000
        )
        
        return await self.send_notification(notification)
    
    async def update_notification(self, notification_id: int, 
                                new_notification: HorizonNotification) -> Optional[int]:
        """Update an existing notification."""
        if notification_id in self.active_notifications:
            new_notification.replace_id = notification_id
            return await self.send_notification(new_notification)
        else:
            return await self.send_notification(new_notification)
    
    async def close_notification(self, notification_id: int):
        """Close a specific notification."""
        try:
            if notification_id in self.active_notifications:
                # There's no standard way to close notifications via notify-send
                # This would typically require D-Bus interface
                del self.active_notifications[notification_id]
                
        except Exception as e:
            print(f"Error closing notification {notification_id}: {e}")
    
    def enable_notifications(self):
        """Enable desktop notifications."""
        self.notifications_enabled = True
        print("Desktop notifications enabled")
    
    def disable_notifications(self):
        """Disable desktop notifications."""
        self.notifications_enabled = False
        print("Desktop notifications disabled")
    
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.notifications_enabled
    
    def get_notification_history(self) -> List[Dict[str, Any]]:
        """Get notification history."""
        return self.notification_history.copy()
    
    def clear_notification_history(self):
        """Clear notification history."""
        self.notification_history.clear()
        print("Notification history cleared")
    
    async def test_notifications(self):
        """Test notification system with sample notifications."""
        test_notifications = [
            HorizonNotification(
                title="Test Notification",
                message="This is a test notification to verify the system is working",
                urgency=NotificationUrgency.NORMAL
            ),
            HorizonNotification(
                title="AI Response Test",
                message="This simulates an AI response notification",
                category=NotificationCategory.AI_RESPONSE,
                urgency=NotificationUrgency.NORMAL
            ),
            HorizonNotification(
                title="Error Test",
                message="This is a test error notification",
                category=NotificationCategory.ERROR,
                urgency=NotificationUrgency.CRITICAL,
                icon="dialog-error"
            )
        ]
        
        for i, notification in enumerate(test_notifications):
            notification_id = await self.send_notification(notification)
            if notification_id:
                print(f"Test notification {i+1} sent with ID: {notification_id}")
            else:
                print(f"Failed to send test notification {i+1}")
            
            # Wait between notifications
            await asyncio.sleep(2)
    
    async def send_startup_notification(self):
        """Send notification when Horizon starts up."""
        notification = HorizonNotification(
            title="Horizon AI Assistant",
            message="AI Assistant is now running in the background",
            urgency=NotificationUrgency.LOW,
            timeout=4000
        )
        
        return await self.send_notification(notification)
    
    async def send_shutdown_notification(self):
        """Send notification when Horizon shuts down."""
        notification = HorizonNotification(
            title="Horizon AI Assistant",
            message="AI Assistant has been stopped",
            urgency=NotificationUrgency.LOW,
            timeout=3000
        )
        
        return await self.send_notification(notification)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total_sent = len(self.notification_history)
        
        # Count by category
        category_counts = {}
        urgency_counts = {}
        
        for notif in self.notification_history:
            category = notif.get('category', 'unknown')
            urgency = notif.get('urgency', 'unknown')
            
            category_counts[category] = category_counts.get(category, 0) + 1
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
        
        return {
            'total_sent': total_sent,
            'active_notifications': len(self.active_notifications),
            'notifications_enabled': self.notifications_enabled,
            'by_category': category_counts,
            'by_urgency': urgency_counts,
            'last_notification': self.notification_history[-1] if self.notification_history else None
        }
    
    async def cleanup(self):
        """Clean up notification resources."""
        # Close all active notifications
        self.active_notifications.clear()
        
        # Send shutdown notification
        await self.send_shutdown_notification()
        
        print("Notification manager cleaned up")