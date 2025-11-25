"""
Audiobookshelf player for podcast playback using MPD
"""

import asyncio
import mpd
import aiohttp
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class AudiobookshelfPlayer:
    """Player for Audiobookshelf podcasts using MPD"""

    def __init__(self):
        self.volume = 0.5
        self.current_url: Optional[str] = None
        self.current_item_id: Optional[str] = None
        self.playing = False
        self.position = 0.0
        self.mpd_client: Optional[mpd.MPDClient] = None
        self.mpd_host = "localhost"
        self.mpd_port = 6600
        self._connected = False
        self.audiobookshelf_host = "bigboy"
        self.audiobookshelf_port = 13378
        self.audiobookshelf_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlJZCI6ImNkNDcxNzlkLWNkOGUtNDNlYy05NGY1LTI3MDZlY2M3OTY5ZCIsIm5hbWUiOiJyYWRpbyIsInR5cGUiOiJhcGkiLCJpYXQiOjE3NjQwMjE3ODR9.MjWYsDQc6iXnxbCK_0aR2UuiyBO5QdBzYfqxpw6IeQc"

    async def initialize(self) -> bool:
        """Initialize Audiobookshelf player with MPD connection"""
        try:
            logger.info("Initializing Audiobookshelf player with MPD...")

            # Initialize MPD client
            self.mpd_client = mpd.MPDClient()
            self.mpd_client.timeout = 10
            self.mpd_client.idletimeout = None

            # Connect to MPD
            await self._connect_mpd()

            # Set initial volume
            await self.set_volume(self.volume)

            logger.info("Audiobookshelf player initialized with MPD")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Audiobookshelf player: {e}")
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
                self.current_item_id = item_url.split("/item/")[-1].split("?")[0]
            else:
                self.current_item_id = item_url

            # Get stream URL from Audiobookshelf API
            headers = {"Authorization": f"Bearer {self.audiobookshelf_token}"}
            api_url = f"http://{self.audiobookshelf_host}:{self.audiobookshelf_port}/api/items/{self.current_item_id}/download"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        # The response might be a redirect to the actual stream
                        if response.status == 302:
                            stream_url = response.headers.get("Location")
                        else:
                            # If no redirect, use the API URL directly
                            stream_url = api_url

                        logger.info(f"Got stream URL: {stream_url}")
                        return stream_url
                    else:
                        logger.error(f"Failed to get stream URL: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            return None

    async def play(self, item_url: str) -> bool:
        """Play Audiobookshelf item"""
        try:
            logger.info(f"Starting Audiobookshelf item: {item_url}")

            # Get the actual stream URL
            stream_url = await self._get_stream_url(item_url)
            if not stream_url:
                logger.error("Could not get stream URL for Audiobookshelf item")
                return False

            await self._ensure_connection()

            # Clear current playlist
            self.mpd_client.clear()

            # Add the audiobook stream to playlist
            self.mpd_client.add(stream_url)

            # Start playback
            self.mpd_client.play()

            self.current_url = stream_url
            self.playing = True
            self.position = 0.0

            logger.info(f"Audiobookshelf playback started: {item_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to play Audiobookshelf item: {e}")
            return False

    async def stop(self) -> None:
        """Stop playback and save position"""
        try:
            if self.playing:
                await self._ensure_connection()

                # Get current position before stopping
                status = self.mpd_client.status()
                if status.get("state") == "play":
                    self.position = float(status.get("elapsed", 0))

                self.mpd_client.stop()
                self.mpd_client.clear()

                # TODO: Save position to Audiobookshelf API
                await self._save_position()

                self.playing = False
                self.current_url = None
                logger.info("Audiobookshelf playback stopped")

        except Exception as e:
            logger.error(f"Error stopping Audiobookshelf playback: {e}")

    async def pause(self) -> None:
        """Pause playback and save position"""
        try:
            if self.playing:
                await self._ensure_connection()

                # Get current position before pausing
                status = self.mpd_client.status()
                if status.get("state") == "play":
                    self.position = float(status.get("elapsed", 0))

                self.mpd_client.pause()
                self.playing = False

                # TODO: Save position to Audiobookshelf API
                await self._save_position()

                logger.info("Audiobookshelf playback paused")

        except Exception as e:
            logger.error(f"Error pausing Audiobookshelf playback: {e}")

    async def resume(self) -> None:
        """Resume playback"""
        try:
            if not self.playing and self.current_url:
                await self._ensure_connection()

                # Get saved position from Audiobookshelf API
                saved_position = await self._get_saved_position()
                if saved_position > 0:
                    self.mpd_client.seekcur(saved_position)
                    self.position = saved_position

                self.mpd_client.pause(0)  # 0 = unpause
                self.playing = True

                logger.info(f"Audiobookshelf playback resumed from {saved_position}s")

        except Exception as e:
            logger.error(f"Error resuming Audiobookshelf playback: {e}")

    async def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        try:
            self.volume = max(0.0, min(1.0, volume))

            await self._ensure_connection()
            # Convert 0.0-1.0 to 0-100 for MPD
            mpd_volume = int(self.volume * 100)
            self.mpd_client.setvol(mpd_volume)

            logger.info(f"Audiobookshelf volume set to {self.volume} ({mpd_volume}%)")

        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    async def _save_position(self) -> None:
        """Save current position to Audiobookshelf"""
        try:
            if self.current_item_id and self.position > 0:
                headers = {"Authorization": f"Bearer {self.audiobookshelf_token}"}
                api_url = f"http://{self.audiobookshelf_host}:{self.audiobookshelf_port}/api/me/progress/{self.current_item_id}"

                payload = {
                    "currentTime": self.position,
                    "isFinished": False,
                    "lastUpdate": int(asyncio.get_event_loop().time()),
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_url, json=payload, headers=headers
                    ) as response:
                        if response.status == 200:
                            logger.info(
                                f"Saved position {self.position}s for item {self.current_item_id}"
                            )
                        else:
                            logger.error(f"Failed to save position: {response.status}")

        except Exception as e:
            logger.error(f"Error saving position: {e}")

    async def _get_saved_position(self) -> float:
        """Get saved position from Audiobookshelf"""
        try:
            if not self.current_item_id:
                return 0.0

            headers = {"Authorization": f"Bearer {self.audiobookshelf_token}"}
            api_url = f"http://{self.audiobookshelf_host}:{self.audiobookshelf_port}/api/me/progress/{self.current_item_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get("currentTime", 0.0))
                    else:
                        logger.warning(
                            f"Failed to get saved position: {response.status}"
                        )
                        return 0.0

        except Exception as e:
            logger.error(f"Error getting saved position: {e}")
            return 0.0

    async def get_item_info(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an Audiobookshelf item"""
        try:
            headers = {"Authorization": f"Bearer {self.audiobookshelf_token}"}
            api_url = f"http://{self.audiobookshelf_host}:{self.audiobookshelf_port}/api/items/{item_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "id": data.get("id"),
                            "title": data.get("title"),
                            "author": data.get("author"),
                            "duration": data.get("duration"),
                            "type": data.get("mediaType", "unknown"),
                            "description": data.get("description", ""),
                        }
                    else:
                        logger.error(f"Failed to get item info: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error getting item info: {e}")
            return None

            headers = {"Authorization": f"Bearer {self.audiobookshelf_token}"}
            api_url = f"http://{self.audiobookshelf_host}:{self.audiobookshelf_port}/api/me/progress/{self.current_item_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get("currentTime", 0.0))
                    else:
                        logger.warning(
                            f"Failed to get saved position: {response.status}"
                        )
                        return 0.0

        except Exception as e:
            logger.error(f"Error getting saved position: {e}")
            return 0.0

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
                "current_item_id": self.current_item_id,
                "elapsed": float(status.get("elapsed", 0)),
                "duration": float(status.get("duration", 0)),
                "position": self.position,
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"state": "error"}

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            await self.stop()

            if self._connected and self.mpd_client:
                self.mpd_client.close()
                self.mpd_client.disconnect()
                self._connected = False

            logger.info("Audiobookshelf player cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
