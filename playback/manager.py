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
        self.mpd_client = None

        # Initialize single unified player
        from playback.unified.player import UnifiedPlayer

        self.player = UnifiedPlayer(config_manager)

    async def initialize(self) -> bool:
        """Initialize all playback components"""
        try:
            logger.info("Initializing playback manager...")

            # Initialize unified player
            await self.player.initialize()

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

            # Start playback
            self.state = PlaybackState.BUFFERING
            self.current_source = audio_source

            success = await self.player.play(audio_source)

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
            if self.player and self.state != PlaybackState.STOPPED:
                logger.info("Stopping current playback...")
                await self.player.stop()

            self.state = PlaybackState.STOPPED
            self.current_source = None

        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    async def pause(self) -> None:
        """Pause current playback"""
        try:
            if self.player and self.state == PlaybackState.PLAYING:
                await self.player.pause()
                self.state = PlaybackState.PAUSED

        except Exception as e:
            logger.error(f"Error pausing playback: {e}")

    async def resume(self) -> None:
        """Resume paused playback"""
        try:
            if self.player and self.state == PlaybackState.PAUSED:
                await self.player.resume()
                self.state = PlaybackState.PLAYING

        except Exception as e:
            logger.error(f"Error resuming playback: {e}")

    async def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        try:
            volume = max(0.0, min(1.0, volume))

            if self.player:
                await self.player.set_volume(volume)

            logger.info(f"Volume set to {volume}")

        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    async def cleanup(self) -> None:
        """Clean up playback resources"""
        try:
            await self.stop()
            await self.player.cleanup()
            logger.info("Playback manager cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        try:
            if self.player:
                player_status = await self.player.get_status()
                return {
                    "state": self.state.value,
                    "current_source": self.current_source,
                    "current_player": "UnifiedPlayer",
                    "volume": getattr(self.player, "volume", 0.5),
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
                "current_player": "UnifiedPlayer",
                "volume": 0.5,
            }
