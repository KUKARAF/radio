"""
Radio player for internet radio streams using MPD
"""

import asyncio
import mpd
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class RadioPlayer:
    """Player for internet radio streams using MPD"""

    def __init__(self):
        self.volume = 0.5
        self.current_url: Optional[str] = None
        self.playing = False
        self.mpd_client: Optional[mpd.MPDClient] = None
        self.mpd_host = "localhost"
        self.mpd_port = 6600
        self._connected = False

    async def initialize(self) -> bool:
        """Initialize radio player with MPD connection"""
        try:
            logger.info("Initializing radio player with MPD...")

            # Initialize MPD client
            self.mpd_client = mpd.MPDClient()
            self.mpd_client.timeout = 10
            self.mpd_client.idletimeout = None

            # Connect to MPD
            await self._connect_mpd()

            # Set initial volume
            await self.set_volume(self.volume)

            logger.info("Radio player initialized with MPD")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize radio player: {e}")
            return False

    async def _connect_mpd(self) -> None:
        """Connect to MPD server"""
        try:
            if not self._connected:
                self.mpd_client.connect(self.mpd_host, self.mpd_port)
                self._connected = True
                logger.info(f"Connected to MPD at {self.mpd_host}:{self.mpd_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MPD: {e}")
            raise

    async def _ensure_connection(self) -> None:
        """Ensure MPD connection is active"""
        try:
            if not self._connected or not self.mpd_client.ping():
                self._connected = False
                await self._connect_mpd()
        except Exception:
            self._connected = False
            await self._connect_mpd()

    async def play(self, stream_url: str) -> bool:
        """Play radio stream"""
        try:
            logger.info(f"Starting radio stream: {stream_url}")
            await self._ensure_connection()

            # Clear current playlist
            self.mpd_client.clear()

            # Add the radio stream to playlist
            self.mpd_client.add(stream_url)

            # Start playback
            self.mpd_client.play()

            self.current_url = stream_url
            self.playing = True

            logger.info(f"Radio playback started: {stream_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to play radio stream: {e}")
            return False

    async def stop(self) -> None:
        """Stop playback"""
        try:
            if self.playing:
                await self._ensure_connection()
                self.mpd_client.stop()
                self.mpd_client.clear()

                self.playing = False
                self.current_url = None
                logger.info("Radio playback stopped")

        except Exception as e:
            logger.error(f"Error stopping radio playback: {e}")

    async def pause(self) -> None:
        """Pause playback"""
        try:
            if self.playing:
                await self._ensure_connection()
                self.mpd_client.pause()
                logger.info("Radio playback paused")

        except Exception as e:
            logger.error(f"Error pausing radio playback: {e}")

    async def resume(self) -> None:
        """Resume playback"""
        try:
            if not self.playing and self.current_url:
                await self._ensure_connection()
                self.mpd_client.pause(0)  # 0 = unpause
                self.playing = True
                logger.info("Radio playback resumed")

        except Exception as e:
            logger.error(f"Error resuming radio playback: {e}")

    async def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        try:
            self.volume = max(0.0, min(1.0, volume))

            await self._ensure_connection()
            # Convert 0.0-1.0 to 0-100 for MPD
            mpd_volume = int(self.volume * 100)
            self.mpd_client.setvol(mpd_volume)

            logger.info(f"Radio volume set to {self.volume} ({mpd_volume}%)")

        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    async def get_status(self) -> dict:
        """Get current MPD status"""
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
            }

        except Exception as e:
            logger.error(f"Error getting MPD status: {e}")
            return {"state": "error"}

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            await self.stop()

            if self._connected and self.mpd_client:
                self.mpd_client.close()
                self.mpd_client.disconnect()
                self._connected = False

            logger.info("Radio player cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
