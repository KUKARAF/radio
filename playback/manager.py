"""
Playback manager for smart radio system
Handles audio playback from various sources
"""

import asyncio
from typing import Optional, Dict, Any
from enum import Enum

from playback.radio.player import RadioPlayer
from playback.audiobookshelf.player import AudiobookshelfPlayer
from utils.logger import get_logger

logger = get_logger(__name__)


class PlaybackState(Enum):
    """Playback states"""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"


class PlaybackManager:
    """Main playback manager for all audio sources"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.state = PlaybackState.STOPPED
        self.current_source: Optional[str] = None
        self.current_player: Optional[RadioPlayer | AudiobookshelfPlayer] = None

        # Initialize players
        self.radio_player = RadioPlayer()
        self.audiobookshelf_player = AudiobookshelfPlayer()

    async def initialize(self) -> bool:
        """Initialize all playback components"""
        try:
            logger.info("Initializing playback manager...")

            await self.radio_player.initialize()
            await self.audiobookshelf_player.initialize()

            logger.info("Playback manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize playback manager: {e}")
            return False

    async def play(self, audio_source: str) -> bool:
        """Play audio from specified source"""
        try:
            logger.info(f"Starting playback: {audio_source}")

            # Stop current playback
            await self.stop()

            # Determine source type and appropriate player
            if audio_source.startswith(("http://", "https://")):
                if "audiobookshelf" in audio_source.lower():
                    self.current_player = self.audiobookshelf_player
                else:
                    self.current_player = self.radio_player
            else:
                logger.error(f"Unsupported audio source format: {audio_source}")
                return False

            # Start playback
            self.state = PlaybackState.BUFFERING
            self.current_source = audio_source

            success = await self.current_player.play(audio_source)

            if success:
                self.state = PlaybackState.PLAYING
                logger.info(f"Playback started: {audio_source}")
            else:
                self.state = PlaybackState.ERROR
                logger.error(f"Failed to start playback: {audio_source}")

            return success

        except Exception as e:
            logger.error(f"Error during playback: {e}")
            self.state = PlaybackState.ERROR
            return False

    async def stop(self) -> None:
        """Stop current playback"""
        try:
            if self.current_player and self.state != PlaybackState.STOPPED:
                logger.info("Stopping current playback...")
                await self.current_player.stop()

            self.state = PlaybackState.STOPPED
            self.current_source = None
            self.current_player = None

        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    async def pause(self) -> None:
        """Pause current playback"""
        try:
            if self.current_player and self.state == PlaybackState.PLAYING:
                await self.current_player.pause()
                self.state = PlaybackState.PAUSED

        except Exception as e:
            logger.error(f"Error pausing playback: {e}")

    async def resume(self) -> None:
        """Resume paused playback"""
        try:
            if self.current_player and self.state == PlaybackState.PAUSED:
                await self.current_player.resume()
                self.state = PlaybackState.PLAYING

        except Exception as e:
            logger.error(f"Error resuming playback: {e}")

    async def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        try:
            volume = max(0.0, min(1.0, volume))

            if self.current_player:
                await self.current_player.set_volume(volume)

            logger.info(f"Volume set to {volume}")

        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    async def cleanup(self) -> None:
        """Clean up playback resources"""
        try:
            await self.stop()
            await self.radio_player.cleanup()
            await self.audiobookshelf_player.cleanup()
            logger.info("Playback manager cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        try:
            if self.current_player:
                player_status = await self.current_player.get_status()
                return {
                    "state": self.state.value,
                    "current_source": self.current_source,
                    "current_player": type(self.current_player).__name__,
                    "volume": getattr(self.current_player, "volume", 0.5),
                    **player_status,
                }
            else:
                return {
                    "state": self.state.value,
                    "current_source": None,
                    "current_player": None,
                    "volume": 0.5,
                }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "state": PlaybackState.ERROR.value,
                "current_source": self.current_source,
                "current_player": type(self.current_player).__name__
                if self.current_player
                else None,
                "volume": 0.5,
            }
