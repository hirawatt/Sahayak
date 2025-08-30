"""
Voice Input Manager for Horizon Overlay using sounddevice.
Handles voice activation detection and audio capture.
"""

import asyncio
import threading
import numpy as np
import sounddevice as sd
from typing import Optional, Callable, Dict, Any
import queue
import time

class VoiceInputManager:
    """Manages voice input and activation detection."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 block_size: int = 1024,
                 voice_threshold: float = 0.01,
                 silence_duration: float = 2.0):
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.voice_threshold = voice_threshold
        self.silence_duration = silence_duration
        
        self.is_recording = False
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.callbacks: Dict[str, Callable] = {}
        
        # Voice activity detection state
        self.last_voice_time = 0
        self.is_speaking = False
        self.speech_buffer = []
        
        # Audio stream
        self.stream = None
        
    def list_audio_devices(self) -> Dict[int, Dict[str, Any]]:
        """List available audio input devices."""
        devices = {}
        device_list = sd.query_devices()
        
        for i, device in enumerate(device_list):
            if device['max_input_channels'] > 0:  # Input device
                devices[i] = {
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate'],
                    'hostapi': device['hostapi']
                }
        
        return devices
    
    def set_input_device(self, device_id: Optional[int] = None):
        """Set the audio input device."""
        if device_id is not None:
            sd.default.device[0] = device_id
        else:
            # Use default device
            sd.default.device[0] = None
    
    def _audio_callback(self, indata, frames, time, status):
        """Audio stream callback for real-time processing."""
        if status:
            print(f"Audio callback status: {status}")
        
        # Calculate RMS (Root Mean Square) for voice activity detection
        rms = np.sqrt(np.mean(indata**2))
        
        # Voice activity detection
        current_time = time.inputBufferAdcTime
        
        if rms > self.voice_threshold:
            self.last_voice_time = current_time
            if not self.is_speaking:
                self.is_speaking = True
                self._trigger_callback('voice_start')
            
            # Add audio to buffer if recording
            if self.is_recording:
                self.speech_buffer.append(indata.copy())
        
        else:
            # Check for end of speech
            if self.is_speaking and (current_time - self.last_voice_time) > self.silence_duration:
                self.is_speaking = False
                self._trigger_callback('voice_end')
                
                # Process recorded audio if available
                if self.is_recording and self.speech_buffer:
                    self._process_recorded_audio()
    
    def _process_recorded_audio(self):
        """Process the recorded audio buffer."""
        if not self.speech_buffer:
            return
        
        # Concatenate audio buffer
        audio_data = np.concatenate(self.speech_buffer, axis=0)
        self.speech_buffer.clear()
        
        # Trigger callback with audio data
        self._trigger_callback('audio_recorded', {'audio': audio_data})
    
    def _trigger_callback(self, event: str, data: Optional[Dict] = None):
        """Trigger registered callbacks for events."""
        if event in self.callbacks:
            try:
                if data:
                    threading.Thread(target=self.callbacks[event], args=(data,), daemon=True).start()
                else:
                    threading.Thread(target=self.callbacks[event], daemon=True).start()
            except Exception as e:
                print(f"Error executing voice callback: {e}")
    
    def start_listening(self) -> bool:
        """Start listening for voice activity."""
        try:
            if self.is_listening:
                return True
            
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.block_size,
                callback=self._audio_callback,
                dtype=np.float32
            )
            
            self.stream.start()
            self.is_listening = True
            print(f"Voice input started - Sample rate: {self.sample_rate}Hz")
            return True
            
        except Exception as e:
            print(f"Error starting voice input: {e}")
            return False
    
    def stop_listening(self):
        """Stop listening for voice activity."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        self.is_listening = False
        self.is_recording = False
        self.speech_buffer.clear()
        print("Voice input stopped")
    
    def start_recording(self):
        """Start recording voice input."""
        if not self.is_listening:
            if not self.start_listening():
                return False
        
        self.is_recording = True
        self.speech_buffer.clear()
        print("Voice recording started")
        return True
    
    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return the recorded audio."""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        
        if self.speech_buffer:
            audio_data = np.concatenate(self.speech_buffer, axis=0)
            self.speech_buffer.clear()
            print(f"Voice recording stopped - {len(audio_data)} samples")
            return audio_data
        
        return None
    
    def save_audio(self, audio_data: np.ndarray, filename: str):
        """Save audio data to a WAV file."""
        try:
            import soundfile as sf
            sf.write(filename, audio_data, self.sample_rate)
            print(f"Audio saved to {filename}")
        except ImportError:
            print("soundfile library not available for saving audio")
        except Exception as e:
            print(f"Error saving audio: {e}")
    
    def set_voice_threshold(self, threshold: float):
        """Set the voice activity detection threshold."""
        self.voice_threshold = threshold
    
    def set_silence_duration(self, duration: float):
        """Set the silence duration for end-of-speech detection."""
        self.silence_duration = duration
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for voice events.
        
        Events:
        - 'voice_start': Triggered when voice activity begins
        - 'voice_end': Triggered when voice activity ends
        - 'audio_recorded': Triggered when audio recording is complete
        """
        self.callbacks[event] = callback
    
    def unregister_callback(self, event: str):
        """Unregister a callback for voice events."""
        if event in self.callbacks:
            del self.callbacks[event]
    
    def test_audio_input(self, duration: float = 3.0):
        """Test audio input by recording for a specified duration."""
        print(f"Testing audio input for {duration} seconds...")
        
        # Record audio
        audio_data = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32
        )
        sd.wait()  # Wait for recording to complete
        
        # Calculate statistics
        rms = np.sqrt(np.mean(audio_data**2))
        max_amplitude = np.max(np.abs(audio_data))
        
        print(f"Test complete:")
        print(f"  RMS: {rms:.6f}")
        print(f"  Max amplitude: {max_amplitude:.6f}")
        print(f"  Voice threshold: {self.voice_threshold:.6f}")
        print(f"  Voice detected: {'Yes' if rms > self.voice_threshold else 'No'}")
        
        return audio_data, rms, max_amplitude
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get information about the current audio setup."""
        try:
            default_device = sd.query_devices(kind='input')
            return {
                'device_name': default_device['name'],
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'block_size': self.block_size,
                'voice_threshold': self.voice_threshold,
                'silence_duration': self.silence_duration,
                'is_listening': self.is_listening,
                'is_recording': self.is_recording
            }
        except Exception as e:
            return {'error': str(e)}