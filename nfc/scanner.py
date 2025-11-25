"""
NFC Scanner module for smart radio system
Handles NFC card detection using PN532
"""

import asyncio
import time
from typing import Callable, Optional, Dict, Any
from enum import Enum

try:
    import adafruit_pn532
    import board
    import busio

    PN532_AVAILABLE = True
except ImportError:
    PN532_AVAILABLE = False

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
    """NFC scanner with PN532 interface and card management"""

    def __init__(self, gpio_sda: int = 8, gpio_scl: int = 12, config_manager=None):
        self.gpio_sda = gpio_sda
        self.gpio_scl = gpio_scl
        self.config_manager = config_manager
        self.state = NFCState.IDLE
        self.card_handlers: list[Callable[[str], None]] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_card_id: Optional[str] = None
        self.last_card_time: float = 0
        self.debounce_interval: float = 2.0  # seconds

        # PN532 hardware
        self.pn532 = None
        self._mock_mode = not PN532_AVAILABLE
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

            # Initialize PN532 hardware
            if self._mock_mode:
                logger.info("Using mock NFC mode for development (PN532 not available)")
            else:
                logger.info("Initializing PN532 NFC reader...")
                await self._initialize_pn532()

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

    async def _initialize_pn532(self) -> None:
        """Initialize PN532 NFC reader"""
        try:
            # Create I2C bus using Adafruit Blinka with specific pins
            # Note: Using board.D2 and D3 for I2C (SCL=3, SDA=2 on Pi)
            i2c = busio.I2C(board.D2, board.D3)

            # Initialize PN532
            self.pn532 = adafruit_pn532.PN532_I2C(i2c)

            # Configure PN532 for I2C mode
            self.pn532.SAM_configuration()

            # Test communication
            version = self.pn532.firmware_version
            if version:
                logger.info(
                    f"PN532 initialized successfully on I2C (SCL=12, SDA=8), firmware version: {version}"
                )
            else:
                raise Exception("Failed to communicate with PN532")

        except Exception as e:
            logger.error(f"Failed to initialize PN532: {e}")
            raise

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
        """Scan for NFC card and return URL directly from tag"""
        if self._mock_mode:
            # Simulate random card detection for testing
            import random

            if random.random() < 0.01:  # 1% chance per scan
                return random.choice(self._mock_cards)
        else:
            # Use PN532 to scan for cards and read NDEF records
            try:
                # Poll for NFC card
                uid = self.pn532.read_passive_target(timeout=0.1)
                if uid:
                    # Convert UID bytes to hex string for logging
                    card_id = "".join([f"{byte:02X}" for byte in uid])
                    logger.info(f"NFC card detected: {card_id}")

                    # Try to read NDEF records from the card
                    try:
                        # Read NDEF data from card
                        ndef_data = self.pn532.ntag2xx_read()
                        if ndef_data:
                            # Parse NDEF records to find URL
                            url = self._parse_ndef_url(ndef_data)
                            if url:
                                logger.info(f"Found URL in NFC tag: {url}")
                                return url
                            else:
                                logger.info("No URL found in NDEF data")
                        else:
                            logger.info("No NDEF data found on card")
                    except Exception as e:
                        logger.debug(f"Error reading NDEF data: {e}")

                    # Return card ID as fallback for config lookup
                    return card_id
            except Exception as e:
                logger.debug(f"NFC scan error: {e}")

        return None

    def _parse_ndef_url(self, ndef_data: bytes) -> Optional[str]:
        """Parse NDEF data to extract URL"""
        try:
            # Simple NDEF URL parsing
            # NDEF URL records start with 0xD1 (MB=1, ME=0, SR=1, TN=1)
            # followed by type length (1 byte), payload type (U for URL), and URL

            if len(ndef_data) < 5:
                return None

            # Check for NDEF URL record
            if ndef_data[0] == 0xD1:  # NDEF record header
                type_length = ndef_data[1]
                if type_length == 1 and ndef_data[2] == ord("U"):  # URL type
                    url_length = ndef_data[3]
                    if len(ndef_data) >= 4 + url_length:
                        url = ndef_data[4 : 4 + url_length].decode("utf-8")
                        return url

        except Exception as e:
            logger.debug(f"Error parsing NDEF URL: {e}")

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
