"""
NFC Scanner module for smart radio system
Handles NFC card detection using PN532 with SMBus
"""

import asyncio
import time
import smbus
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
    """NFC scanner with PN532 interface and card management"""

    def __init__(self):
        # Hardware GPIO pins for NFC scanner (SDA=2, SCL=3)
        self.gpio_sda = 2
        self.gpio_scl = 3
        self.state = NFCState.IDLE
        self.card_handlers: list[Callable[[str], None]] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_card_id: Optional[str] = None
        self.last_card_time: float = 0
        self.debounce_interval: float = 2.0  # seconds

        # PN532 hardware
        self.pn532 = None
        self.pn532_addr = 0x24
        self._mock_mode = False
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
        try:
            # Use SMBus to check I2C availability (I2C-1 for GPIO 2,3)
            bus = smbus.SMBus(1)

            # Test I2C communication
            bus.read_byte(0x24)

            logger.info("GPIO availability check passed")
            return True

        except Exception as e:
            logger.error(f"GPIO availability check failed: {e}")
            return False

    async def _initialize_pn532(self) -> None:
        """Initialize PN532 NFC reader using SMBus"""
        try:
            import smbus

            # Create I2C bus using SMBus (I2C-1 for GPIO 2,3)
            self.bus = smbus.SMBus(1)
            self.pn532_addr = 0x24

            # Test communication with PN532
            version = self.bus.read_byte_data(self.pn532_addr, 0x00)
            logger.info(f"PN532 firmware version: 0x{version:02x}")

            # Configure PN532 for I2C mode
            self.bus.write_byte_data(self.pn532_addr, 0x01, 0x00)  # SAM config
            time.sleep(0.1)

            logger.info("PN532 initialized successfully with SMBus")

        except Exception as e:
            logger.error(f"Failed to initialize PN532: {e}")
            raise

    async def _monitor_loop(self) -> None:
        """Main NFC monitoring loop"""
        logger.info("Starting NFC monitoring loop")

        while self.state == NFCState.SCANNING:
            try:
                if self._mock_mode:
                    # Simulate card detection in mock mode
                    await asyncio.sleep(1)
                    card_id = self._mock_cards[int(time.time()) % len(self._mock_cards)]
                    logger.info(f"Mock NFC card detected: {card_id}")
                else:
                    # Real PN532 polling
                    if self.pn532:
                        # Simple polling approach
                        try:
                            # Try to read a card (this will return data if card is present)
                            data = self.bus.read_i2c_block_data(self.pn532_addr, 16)

                            if data and len(data) > 0:
                                # Convert to hex string for card ID
                                card_id = "".join(
                                    [f"{byte:02x}" for byte in data if byte != 0]
                                )

                                # Debounce
                                current_time = time.time()
                                if (
                                    card_id != self.last_card_id
                                    and current_time - self.last_card_time
                                    > self.debounce_interval
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
                                            logger.error(f"Card handler error: {e}")
                        except Exception as e:
                            logger.debug(f"NFC read error: {e}")

                await asyncio.sleep(0.1)  # Polling interval

            except Exception as e:
                logger.error(f"NFC monitoring error: {e}")
                await asyncio.sleep(1)

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

    async def stop(self) -> None:
        """Stop NFC monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        self.state = NFCState.IDLE
        logger.info("NFC scanner stopped")

    async def get_card_info(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered card"""
        try:
            if not self.config_manager:
                return None

            return await self.config_manager.get_card_mapping(card_id)
        except Exception as e:
            logger.error(f"Failed to get card info: {e}")
            return None
