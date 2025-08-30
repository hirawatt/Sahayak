"""
Setup Wizard for Constella Horizon
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QCheckBox, QSpinBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SetupWizard(QDialog):
    """Setup wizard dialog"""
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Constella Horizon Setup")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Welcome to Constella Horizon")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Let's configure your AI assistant for optimal performance.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # Backend settings
        backend_group = QGroupBox("Backend Configuration")
        backend_layout = QFormLayout()
        
        self.host_input = QLineEdit("localhost")
        backend_layout.addRow("Backend Host:", self.host_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1000, 65535)
        self.port_input.setValue(8000)
        backend_layout.addRow("Backend Port:", self.port_input)
        
        backend_group.setLayout(backend_layout)
        layout.addWidget(backend_group)
        
        # Features settings
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout()
        
        self.enable_hotkeys = QCheckBox("Enable global hotkeys")
        self.enable_hotkeys.setChecked(True)
        features_layout.addWidget(self.enable_hotkeys)
        
        self.enable_auto_context = QCheckBox("Enable automatic context capture")
        self.enable_auto_context.setChecked(True)
        features_layout.addWidget(self.enable_auto_context)
        
        self.enable_voice = QCheckBox("Enable voice input")
        self.enable_voice.setChecked(False)
        features_layout.addWidget(self.enable_voice)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # API Configuration
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout()
        
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setPlaceholderText("sk-...")
        api_layout.addRow("OpenAI API Key:", self.openai_key_input)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.finish_button = QPushButton("Finish Setup")
        self.finish_button.clicked.connect(self.accept)
        self.finish_button.setDefault(True)
        button_layout.addWidget(self.finish_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def accept(self):
        """Save settings and close"""
        # Save backend settings - update the base_url to include host and port
        host = self.host_input.text()
        port = self.port_input.value()
        self.settings.backend.base_url = f"http://{host}:{port}"
        self.settings.backend.websocket_url = f"ws://{host}:{port}/ws"
        
        # Save feature settings
        self.settings.features.enable_hotkeys = self.enable_hotkeys.isChecked()
        self.settings.features.enable_auto_context = self.enable_auto_context.isChecked()
        self.settings.features.enable_voice = self.enable_voice.isChecked()
        
        # Save API keys
        openai_key = self.openai_key_input.text().strip()
        if openai_key:
            from config.settings import APIProvider
            self.settings.set_api_key(APIProvider.OPENAI, openai_key)
        
        super().accept()