"""
Voice input management using sounddevice and numpy
"""

import logging
import asyncio
import threading
from typing import Optional, Callable, List
import queue
import numpy as np
import sounddevice as sd
from dataclasses import dataclass

from config.settings import AudioConfig


@dataclass
class AudioChunk:
    """Represents an audio data chunk"""
    data: np.ndarray
    timestamp: float
    sample_rate: int


class VoiceInputManager:
    """Manages voice input capture using sounddevice"""
    
    def __init__(self, audio_config: AudioConfig):
        self.config = audio_config
        self.logger = logging.getLogger(__name__)
        
        # Recording state
        self.is_recording = False
        self.stream: Optional[sd.InputStream] = None
        self.audio_queue = queue.Queue()
        
        # Callbacks
        self.on_audio_chunk: Optional[Callable[[AudioChunk], None]] = None
        self.on_voice_detected: Optional[Callable[[], None]] = None
        self.on_voice_ended: Optional[Callable[[], None]] = None
        
        # Voice activity detection
        self.vad_enabled = True
        self.silence_threshold = 0.01  # RMS threshold for silence
        self.min_voice_duration = 0.5  # Minimum seconds for voice detection
        self.silence_duration = 1.0    # Seconds of silence before voice end
        
        # Internal state
        self._voice_detected = False
        self._silence_counter = 0
        self._voice_samples = []
        
    def list_devices(self) -> List[dict]:
        """List available audio input devices"""
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'id': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate']
                    })
            
            return input_devices
        except Exception as e:
            self.logger.error(f"Failed to list audio devices: {e}")
            return []
    
    def get_default_device(self) -> Optional[dict]:
        """Get default input device"""
        try:
            device_id = sd.default.device[0]  # Input device
            device_info = sd.query_devices(device_id)
            
            return {
                'id': device_id,
                'name': device_info['name'],
                'channels': device_info['max_input_channels'],
                'sample_rate': device_info['default_samplerate']
            }
        except Exception as e:
            self.logger.error(f"Failed to get default device: {e}")
            return None
    
    async def start_recording(self) -> bool:
        """Start audio recording"""
        if self.is_recording:
            self.logger.warning("Recording already in progress")
            return True
        
        try:
            self.logger.info("Starting voice input recording")
            
            # Configure device
            device_id = self.config.device_id
            if device_id is None:
                # Use default device
                default_device = self.get_default_device()
                if default_device:
                    device_id = default_device['id']
                else:
                    self.logger.error("No audio input device available")
                    return False
            
            # Create input stream
            self.stream = sd.InputStream(
                device=device_id,
                channels=self.config.channels,
                samplerate=self.config.sample_rate,
                blocksize=self.config.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32
            )
            
            # Start the stream
            self.stream.start()
            self.is_recording = True
            
            # Start processing in background
            asyncio.create_task(self._process_audio())
            
            self.logger.info(f"Recording started on device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return False
    
    async def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return
        
        self.logger.info("Stopping voice input recording")
        self.is_recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Clear any remaining audio
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time, status):
        """Callback for audio stream"""
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        
        if self.is_recording:
            # Copy audio data and add to queue
            audio_chunk = AudioChunk(
                data=indata.copy(),
                timestamp=time.inputBufferAdcTime,
                sample_rate=self.config.sample_rate
            )
            
            try:
                self.audio_queue.put_nowait(audio_chunk)
            except queue.Full:
                self.logger.warning("Audio queue full, dropping chunk")
    
    async def _process_audio(self):
        """Process audio chunks from queue"""
        while self.is_recording:
            try:
                # Get audio chunk with timeout
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None, self._get_audio_chunk, 0.1
                )
                
                if chunk is None:
                    continue
                
                # Process the chunk
                await self._handle_audio_chunk(chunk)
                
            except Exception as e:
                self.logger.error(f"Error processing audio: {e}")
                await asyncio.sleep(0.1)
    
    def _get_audio_chunk(self, timeout: float) -> Optional[AudioChunk]:
        """Get audio chunk from queue with timeout"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    async def _handle_audio_chunk(self, chunk: AudioChunk):
        """Handle individual audio chunk"""
        # Call callback if registered
        if self.on_audio_chunk:
            try:
                self.on_audio_chunk(chunk)
            except Exception as e:
                self.logger.error(f"Error in audio chunk callback: {e}")
        
        # Voice Activity Detection
        if self.vad_enabled:
            await self._process_vad(chunk)
    
    async def _process_vad(self, chunk: AudioChunk):
        """Process Voice Activity Detection"""
        # Calculate RMS (Root Mean Square) for volume level
        rms = np.sqrt(np.mean(chunk.data ** 2))
        
        is_voice = rms > self.silence_threshold
        
        if is_voice:
            self._silence_counter = 0
            self._voice_samples.append(chunk)
            
            # Check if voice just started
            if not self._voice_detected:
                # Check if we have enough samples for minimum duration
                total_duration = len(self._voice_samples) * self.config.chunk_size / self.config.sample_rate
                
                if total_duration >= self.min_voice_duration:
                    self._voice_detected = True
                    self.logger.debug("Voice activity detected")
                    
                    if self.on_voice_detected:
                        try:
                            self.on_voice_detected()
                        except Exception as e:
                            self.logger.error(f"Error in voice detected callback: {e}")
        else:
            # Silence detected
            self._silence_counter += 1
            silence_duration = self._silence_counter * self.config.chunk_size / self.config.sample_rate
            
            if self._voice_detected and silence_duration >= self.silence_duration:
                # Voice activity ended
                self._voice_detected = False
                self._silence_counter = 0
                
                self.logger.debug("Voice activity ended")
                
                if self.on_voice_ended:
                    try:
                        self.on_voice_ended()
                    except Exception as e:
                        self.logger.error(f"Error in voice ended callback: {e}")
                
                # Clear voice samples
                self._voice_samples.clear()
    
    def get_voice_audio(self) -> Optional[np.ndarray]:
        """Get collected voice audio data"""
        if not self._voice_samples:
            return None
        
        # Concatenate all voice samples
        audio_data = np.concatenate([chunk.data.flatten() for chunk in self._voice_samples])
        return audio_data
    
    def clear_voice_buffer(self):
        """Clear the voice sample buffer"""
        self._voice_samples.clear()
        self._voice_detected = False
        self._silence_counter = 0
    
    def set_callbacks(self, 
                     on_audio_chunk: Optional[Callable[[AudioChunk], None]] = None,
                     on_voice_detected: Optional[Callable[[], None]] = None,
                     on_voice_ended: Optional[Callable[[], None]] = None):
        """Set callback functions"""
        self.on_audio_chunk = on_audio_chunk
        self.on_voice_detected = on_voice_detected
        self.on_voice_ended = on_voice_ended
    
    def configure_vad(self, 
                     silence_threshold: float = 0.01,
                     min_voice_duration: float = 0.5,
                     silence_duration: float = 1.0):
        """Configure Voice Activity Detection parameters"""
        self.silence_threshold = silence_threshold
        self.min_voice_duration = min_voice_duration
        self.silence_duration = silence_duration
        
        self.logger.info(f"VAD configured: threshold={silence_threshold}, "
                        f"min_duration={min_voice_duration}, silence={silence_duration}")
    
    def get_audio_level(self) -> float:
        """Get current audio level (0.0 to 1.0)"""
        if not self._voice_samples:
            return 0.0
        
        # Get RMS of last chunk
        last_chunk = self._voice_samples[-1]
        rms = np.sqrt(np.mean(last_chunk.data ** 2))
        
        # Normalize to 0-1 range (assuming max RMS of 0.5)
        return min(rms * 2.0, 1.0)
    
    def is_voice_active(self) -> bool:
        """Check if voice is currently being detected"""
        return self._voice_detected