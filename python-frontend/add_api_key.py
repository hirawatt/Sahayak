#!/usr/bin/env python3
"""
Script to add API keys to the settings
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings, APIProvider

def add_api_key():
    """Add an API key interactively"""
    settings = Settings()
    
    print("Available API providers:")
    for provider in APIProvider:
        print(f"  - {provider.value}")
    
    provider_name = input("\nEnter provider name (openai/google/azure): ").strip().lower()
    
    try:
        provider = APIProvider(provider_name)
    except ValueError:
        print(f"Invalid provider: {provider_name}")
        return
    
    api_key = input(f"Enter your {provider.value} API key: ").strip()
    
    if not api_key:
        print("API key cannot be empty")
        return
    
    # Set the API key
    settings.set_api_key(provider, api_key)
    
    print(f"✅ API key for {provider.value} has been saved!")
    print(f"Settings saved to: {settings.config_file}")

if __name__ == "__main__":
    add_api_key()