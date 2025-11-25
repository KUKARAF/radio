"""
Unified Audio Player for Smart Radio
Handles both radio streams and Audiobookshelf items with automatic MPD discovery
"""

import asyncio
import os
import aiohttp
from typing import Optional, Dict, Any
from utils.logger import get_logger
from services.mpd_discovery import MPDDiscovery, MPDConnectionManager

logger = get_logger(__name__)


class UnifiedPlayer:
    """Unified player for all audio sources with automatic MPD discovery"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.volume = 0.5
        self.current_url: Optional[str] = None
        self.playing = False

        # MPD discovery and connection management
        self.mpd_discovery = MPDDiscovery(config_manager)
        self.mpd_connection_manager = MPDConnectionManager(self.mpd_discovery)

        # Audiobookshelf settings
        self.audiobookshelf_host = os.getenv("AUDIOBOOKSHELF_HOST", "bigboy")
        self.audiobookshelf_port = int(os.getenv("AUDIOBOOKSHELF_PORT", "13378"))
        self.audiobookshelf_token = os.getenv("AUDIOBOOKSHELF_TOKEN", "")

    async def initialize(self) -> bool:
        """Initialize the unified player with MPD discovery"""
        try:
            logger.info("Initializing unified audio player with MPD discovery...")

            # Discover and connect to best MPD server
            self.mpd_client = await self.mpd_connection_manager.get_connection()

            if not self.mpd_client:
                logger.error("Failed to connect to any MPD server")
                return False

            # Set initial volume
            await self.set_volume(self.volume)

            logger.info("Unified player initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize unified player: {e}")
            return False

    async def _ensure_connection(self) -> None:
        """Ensure MPD connection is active with automatic failover"""
        try:
            # Get connection with automatic failover
            self.mpd_client = await self.mpd_connection_manager.get_connection()
            if not self.mpd_client:
                raise Exception("No MPD servers available")
        except Exception as e:
            logger.error(f"Failed to ensure MPD connection: {e}")
            raise

    async def _get_stream_url(self, item_url: str) -> Optional[str]:
        """Extract stream URL from Audiobookshelf item"""
        try:
            # If it's already a direct stream URL, return it
            if (
                item_url.startswith(("http://", "https://"))
                and not "audiobookshelf" in item_url.lower()
            ):
                return item_url

            # Extract item ID from Audiobookshelf URL
            if "/item/" in item_url:
                item_id = item_url.split("/item/")[-1].split("?")[0]
            else:
                item_id = item_url

            # Get stream URL from Audiobookshelf API
            headers = {"Authorization": f"Bearer {self.audiobookshelf_token}"}
            api_url = f"http://{self.audiobookshelf_host}:{self.audiobookshelf_port}/api/items/{item_id}/download"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        # Return the API URL directly (MPD will handle the redirect)
                        return api_url
                    else:
                        logger.error(f"Failed to get stream URL: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            return None

    async def _ensure_auth(self, url: str) -> str:
        """Ensure Audiobookshelf URLs have authentication"""
        if "bigboy:13378" in url and "?" not in url:
            # Add authentication token for Audiobookshelf
            auth_token = self.audiobookshelf_token
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}token={auth_token}"
        return url

    async def play(self, audio_source: str) -> bool:
        """Play audio from specified source"""
        try:
            logger.info(f"Starting playback: {audio_source}")
            await self._ensure_connection()

            # Determine source type and get stream URL
            if audio_source.startswith(("http://", "https://")):
                if "audiobookshelf" in audio_source.lower():
                    logger.info("Detected Audiobookshelf source")
                    stream_url = await self._get_stream_url(audio_source)
                    if not stream_url:
                        logger.error("Could not get Audiobookshelf stream URL")
                        return False
                else:
                    logger.info("Detected radio stream source")
                    stream_url = audio_source
            else:
                logger.error(f"Unsupported audio source format: {audio_source}")
                return False

            # Ensure authentication for Audiobookshelf
            final_url = await self._ensure_auth(stream_url)

            # Clear current playlist
            self.mpd_client.clear()

            # Add the URL to playlist
            self.mpd_client.add(final_url)

            # Start playback
            self.mpd_client.play()

            self.current_url = final_url
            self.playing = True

            logger.info(f"Playback started: {final_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            return False

    async def stop(self) -> None:
        """Stop playback"""
        try:
            if self.playing:
                logger.info("Stopping playback...")
                await self._ensure_connection()
                self.mpd_client.stop()
                self.mpd_client.clear()

                self.playing = False
                self.current_url = None
                logger.info("Playback stopped")

        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    async def pause(self) -> None:
        """Pause playback"""
        try:
            if self.playing:
                await self._ensure_connection()
                self.mpd_client.pause()
                logger.info("Playback paused")

        except Exception as e:
            logger.error(f"Error pausing playback: {e}")

    async def resume(self) -> None:
        """Resume playback"""
        try:
            if not self.playing and self.current_url:
                await self._ensure_connection()
                self.mpd_client.pause(0)  # 0 = unpause
                self.playing = True
                logger.info("Playback resumed")

        except Exception as e:
            logger.error(f"Error resuming playback: {e}")

    async def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        try:
            self.volume = max(0.0, min(1.0, volume))

            await self._ensure_connection()
            # Convert 0.0-1.0 to 0-100 for MPD
            mpd_volume = int(self.volume * 100)
            self.mpd_client.setvol(mpd_volume)

            logger.info(f"Volume set to {self.volume} ({mpd_volume}%)")

        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        try:
            await self._ensure_connection()
            status = self.mpd_client.status()
            current_song = self.mpd_client.currentsong()

            return {
                "state": status.get("state", "unknown"),
                "volume": int(status.get("volume", 0)) / 100.0,
                "current_url": current_song.get("file", ""),
                "elapsed": float(status.get("elapsed", 0)),
                "duration": float(status.get("duration", 0)),
                "playing": self.playing,
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"state": "error", "playing": False}

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            await self.stop()
            await self.mpd_connection_manager.close_connection()
            logger.info("Unified player cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
