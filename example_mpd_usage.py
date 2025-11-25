#!/usr/bin/env python3
"""
Example usage of MPD discovery in smart radio main application
"""

import asyncio
from services.mpd_discovery import MPDDiscovery, MPDConnectionManager
from config.manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


class SmartRadioWithMPDDiscovery:
    """Example smart radio with MPD discovery"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.mpd_discovery = MPDDiscovery(self.config_manager)
        self.mpd_connection_manager = MPDConnectionManager(self.mpd_discovery)

    async def initialize(self):
        """Initialize the smart radio with MPD discovery"""
        await self.config_manager.load()

        # Discover and connect to best MPD server
        server = await self.mpd_discovery.discover_best_server()
        if not server:
            raise Exception("No MPD servers available")

        logger.info(f"Smart radio initialized with MPD at {server.host}:{server.port}")
        return True

    async def play_audio(self, audio_url: str):
        """Play audio using discovered MPD server"""
        try:
            # Get MPD connection with automatic failover
            client = await self.mpd_connection_manager.get_connection()

            # Clear current playlist and add new audio
            client.clear()
            client.add(audio_url)
            client.play()

            logger.info(f"Playing audio: {audio_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            return False

    async def get_mpd_status(self):
        """Get current MPD server status"""
        server = await self.mpd_discovery.get_server()
        if server:
            return {
                "host": server.host,
                "port": server.port,
                "response_time": server.response_time,
                "available": server.available,
                "version": server.version,
            }
        return None


async def main():
    """Example usage"""
    radio = SmartRadioWithMPDDiscovery()

    # Initialize
    await radio.initialize()

    # Show MPD status
    status = await radio.get_mpd_status()
    print(f"MPD Server: {status}")

    # Example: Play a radio stream
    # await radio.play_audio("https://streaming.radiostreamlive.com/radiolovelive_devices")


if __name__ == "__main__":
    asyncio.run(main())
