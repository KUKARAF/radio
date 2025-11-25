#!/usr/bin/env python3
"""
Smart Radio Service - Main entry point
Event-driven architecture for NFC-based audio playback system
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

from config.manager import ConfigManager
from nfc.scanner import NFCScanner
from playback.manager import PlaybackManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Web server for monitoring
web_server_task = None


class SmartRadioService:
    """Main service class for Smart Radio system"""

    def __init__(self):
        self.config_manager: Optional[ConfigManager] = None
        self.nfc_scanner: Optional[NFCScanner] = None
        self.playback_manager: Optional[PlaybackManager] = None
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            logger.info("Initializing Smart Radio Service...")

            # Initialize configuration
            self.config_manager = ConfigManager()
            await self.config_manager.load()

            # Initialize playback manager
            self.playback_manager = PlaybackManager(self.config_manager)
            await self.playback_manager.initialize()

            # Initialize NFC scanner with hardware GPIO pins (SDA=2, SCL=3)
            self.nfc_scanner = NFCScanner()
            await self.nfc_scanner.initialize()

            # Set up event handlers
            self.nfc_scanner.register_card_handler(self._handle_nfc_card)

            logger.info("Smart Radio Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            return False

    async def start(self) -> None:
        """Start the main service loop"""
        if not await self.initialize():
            logger.error("Service initialization failed, exiting")
            sys.exit(1)

        self.running = True
        logger.info("Starting Smart Radio Service...")

        try:
            # Start NFC monitoring
            await self.nfc_scanner.start_monitoring()

            # Main service loop
            while self.running and not self._shutdown_event.is_set():
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            await self.shutdown()

    async def _handle_nfc_card(self, card_data: str) -> None:
        """Handle NFC card detection - card_data can be URL or card ID"""
        try:
            logger.info(f"NFC card detected: {card_data}")

            # Check if card_data is a direct URL
            if card_data.startswith(("http://", "https://")):
                # Direct URL from NFC tag
                audio_source = card_data
                logger.info(f"Direct URL from NFC tag: {audio_source}")
            else:
                # Card ID - look up in configuration
                audio_source = await self.config_manager.get_card_mapping(card_data)

                if not audio_source:
                    logger.warning(f"No mapping found for card {card_data}")
                    return

                logger.info(f"Mapped URL for card {card_data}: {audio_source}")

            # Append Audiobookshelf authentication if needed
            audio_source = self._ensure_auth(audio_source)

            logger.info(f"Playing audio source: {audio_source}")

            # Stop current playback and start new source
            await self.playback_manager.stop()
            await self.playback_manager.play(audio_source)

        except Exception as e:
            logger.error(f"Error handling NFC card {card_data}: {e}")

    def _ensure_auth(self, url: str) -> str:
        """Ensure Audiobookshelf URLs have authentication"""
        if "bigboy:13378" in url and "?" not in url:
            # Add authentication token for Audiobookshelf
            auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlJZCI6ImNkNDcxNzlkLWNkOGUtNDNlYy05NGY1LTI3MDZlY2M3OTY5ZCIsIm5hbWUiOiJyYWRpbyIsInR5cGUiOiJhcGkiLCJpYXQiOjE3NjQwMjE3ODR9.MjWYsDQc6iXnxbCK_0aR2UuiyBO5QdBzYfqxpw6IeQc"
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}token={auth_token}"
        return url

    async def shutdown(self) -> None:
        """Gracefully shutdown the service"""
        logger.info("Shutting down Smart Radio Service...")
        self.running = False
        self._shutdown_event.set()

        if self.nfc_scanner:
            await self.nfc_scanner.stop_monitoring()

        if self.playback_manager:
            await self.playback_manager.stop()
            await self.playback_manager.cleanup()

        logger.info("Service shutdown complete")

    async def main():
        """Main entry point"""
        service = SmartRadioService()

        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(service.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start web server in background
        from web_server import SmartRadioWebServer

        web_server = SmartRadioWebServer()
        web_server_task = asyncio.create_task(web_server.main())

        # Start the service
        await service.start()

        # Keep web server running
        try:
            await web_server_task
        except asyncio.CancelledError:
            logger.info("Web server stopped")


if __name__ == "__main__":
    asyncio.run(main())
