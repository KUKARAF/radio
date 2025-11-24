"""
NFC Scanner module for smart radio system
Handles NFC card detection and GPIO interface
"""

import asyncio
import time
from typing import Callable, Optional, Dict, Any
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)


class NFCState(Enum):
    """NFC scanner states"""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    SCANNING = "scanning"
    ERROR = "error"


class NFCScanner:
    """NFC scanner with GPIO interface and card management"""

    def __init__(self, gpio_sda: int = 7, gpio_scl: int = 11, config_manager=None):
        self.gpio_sda = gpio_sda
        self.gpio_scl = gpio_scl
        self.config_manager = config_manager
        self.state = NFCState.IDLE
        self.card_handlers: list[Callable[[str], None]] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_card_id: Optional[str] = None
        self.last_card_time: float = 0
        self.debounce_interval: float = 2.0  # seconds

        # Mock hardware state for development
        self._mock_mode = True
        self._mock_cards = ["A1B2C3D4", "E5F6G7H8", "I9J0K1L2"]

    async def initialize(self) -> bool:
        """Initialize NFC scanner hardware"""
        try:
            self.state = NFCState.INITIALIZING
            logger.info(
                f"Initializing NFC scanner on GPIO {self.gpio_sda}/{self.gpio_scl}"
            )

            # Check GPIO availability
            if not await self._check_gpio_availability():
                logger.error(
                    f"GPIO pins {self.gpio_sda} or {self.gpio_scl} unavailable"
                )
                self.state = NFCState.ERROR
                return False

            # Initialize hardware (mock for now)
            if self._mock_mode:
                logger.info("Using mock NFC mode for development")
            else:
                # TODO: Initialize actual PN532 hardware
                pass

            self.state = NFCState.READY
            logger.info("NFC scanner initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize NFC scanner: {e}")
            self.state = NFCState.ERROR
            return False

    async def _check_gpio_availability(self) -> bool:
        """Check if GPIO pins are available"""
        # Mock implementation - in real hardware would check GPIO
        return True

    def register_card_handler(self, handler: Callable[[str], None]) -> None:
        """Register a callback for NFC card detection"""
        self.card_handlers.append(handler)
        logger.info(f"Registered card handler: {handler.__name__}")

    async def start_monitoring(self) -> None:
        """Start continuous NFC monitoring"""
        if self.state != NFCState.READY:
            logger.error("NFC scanner not ready for monitoring")
            return

        self.state = NFCState.SCANNING
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started NFC monitoring")

    async def stop_monitoring(self) -> None:
        """Stop NFC monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        self.state = NFCState.READY
        logger.info("Stopped NFC monitoring")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop for NFC events"""
        logger.info("Starting NFC monitoring loop")

        while self.state == NFCState.SCANNING:
            try:
                # Check for NFC card (mock implementation)
                card_id = await self._scan_for_card()

                if card_id:
                    current_time = time.time()

                    # Debounce logic
                    if (
                        card_id != self.last_card_id
                        or current_time - self.last_card_time > self.debounce_interval
                    ):
                        self.last_card_id = card_id
                        self.last_card_time = current_time

                        logger.info(f"NFC card detected: {card_id}")

                        # Call all registered handlers
                        for handler in self.card_handlers:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(card_id)
                                else:
                                    handler(card_id)
                            except Exception as e:
                                logger.error(
                                    f"Error in card handler {handler.__name__}: {e}"
                                )

                await asyncio.sleep(0.1)  # Check every 100ms

            except asyncio.CancelledError:
                logger.info("NFC monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in NFC monitoring loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying

    async def _scan_for_card(self) -> Optional[str]:
        """Scan for NFC card (mock implementation)"""
        if self._mock_mode:
            # Simulate random card detection for testing
            import random

            if random.random() < 0.01:  # 1% chance per scan
                return random.choice(self._mock_cards)
        else:
            # TODO: Implement actual NFC scanning
            pass

        return None

    async def register_card(self, card_id: str, audio_source: str) -> bool:
        """Register a new NFC card mapping"""
        try:
            if not self.config_manager:
                logger.error("No config manager available")
                return False

            await self.config_manager.set_card_mapping(card_id, audio_source)
            logger.info(f"Registered card {card_id} -> {audio_source}")
            return True

        except Exception as e:
            logger.error(f"Failed to register card {card_id}: {e}")
            return False

    async def get_card_info(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered card"""
        try:
            if not self.config_manager:
                return None

            mapping = await self.config_manager.get_card_mapping(card_id)
            if mapping:
                return {"card_id": card_id, "audio_source": mapping, "registered": True}
            else:
                return {"card_id": card_id, "audio_source": None, "registered": False}

        except Exception as e:
            logger.error(f"Failed to get card info for {card_id}: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current scanner status"""
        return {
            "state": self.state.value,
            "gpio_sda": self.gpio_sda,
            "gpio_scl": self.gpio_scl,
            "monitoring": self.state == NFCState.SCANNING,
            "last_card_id": self.last_card_id,
            "last_card_time": self.last_card_time,
            "mock_mode": self._mock_mode,
        }
