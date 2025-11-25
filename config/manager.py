"""
Configuration manager for smart radio system
Handles NFC card mappings and system settings
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from utils.logger import get_logger

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Warning: python-dotenv not installed, environment variables may not be loaded"
    )

import os

logger = get_logger(__name__)


class ConfigManager:
    """Configuration manager for NFC card mappings and settings"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self.card_mappings: Dict[str, str] = {}

        # Default configuration
        self.default_config = {
            "nfc": {
                "gpio_sda": 7,
                "gpio_scl": 11,
                "debounce_interval": 2.0,
                "debug_mode": False,
            },
            "audio": {
                "default_volume": 0.5,
                "output_device": "default",
                "buffer_size": 1024,
            },
            "mpd": {
                "discovery_timeout": 3.0,
                "check_interval": 30.0,
                "servers": [
                    {"host": "localhost", "port": 6600},
                    {"host": "radio", "port": 6600},
                ],
            },
            "audiobookshelf": {
                "base_url": os.getenv("AUDIOBOOKSHELF_BASE_URL", ""),
                "username": os.getenv("AUDIOBOOKSHELF_USERNAME", ""),
                "password": os.getenv("AUDIOBOOKSHELF_PASSWORD", ""),
            },
            "cards": {},
        }

    async def load(self) -> bool:
        """Load configuration from file"""
        try:
            logger.info(f"Loading configuration from {self.config_path}")

            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    self.config_data = json.load(f)
                logger.info("Configuration loaded successfully")
            else:
                logger.info("Configuration file not found, creating default")
                self.config_data = self.default_config.copy()
                await self.save()

            # Extract card mappings
            self.card_mappings = self.config_data.get("cards", {})

            return True

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.config_data = self.default_config.copy()
            return False

    async def save(self) -> bool:
        """Save configuration to file"""
        try:
            logger.info(f"Saving configuration to {self.config_path}")

            # Update card mappings in config
            self.config_data["cards"] = self.card_mappings

            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w") as f:
                json.dump(self.config_data, f, indent=2)

            logger.info("Configuration saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    async def get_card_mapping(self, card_id: str) -> Optional[str]:
        """Get audio source mapping for NFC card"""
        return self.card_mappings.get(card_id)

    async def set_card_mapping(self, card_id: str, audio_source: str) -> bool:
        """Set audio source mapping for NFC card"""
        try:
            # Validate audio source format
            if not self._validate_audio_source(audio_source):
                logger.error(f"Invalid audio source format: {audio_source}")
                return False

            self.card_mappings[card_id] = audio_source
            await self.save()

            logger.info(f"Card mapping updated: {card_id} -> {audio_source}")
            return True

        except Exception as e:
            logger.error(f"Failed to set card mapping: {e}")
            return False

    async def remove_card_mapping(self, card_id: str) -> bool:
        """Remove NFC card mapping"""
        try:
            if card_id in self.card_mappings:
                del self.card_mappings[card_id]
                await self.save()
                logger.info(f"Card mapping removed: {card_id}")
                return True
            else:
                logger.warning(f"Card mapping not found: {card_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to remove card mapping: {e}")
            return False

    def get_all_card_mappings(self) -> Dict[str, str]:
        """Get all NFC card mappings"""
        return self.card_mappings.copy()

    def get_nfc_config(self) -> Dict[str, Any]:
        """Get NFC configuration"""
        return self.config_data.get("nfc", self.default_config["nfc"])

    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio configuration"""
        return self.config_data.get("audio", self.default_config["audio"])

    def get_audiobookshelf_config(self) -> Dict[str, Any]:
        """Get Audiobookshelf configuration"""
        return self.config_data.get(
            "audiobookshelf", self.default_config["audiobookshelf"]
        )

    def get_mpd_config(self) -> Dict[str, Any]:
        """Get MPD configuration"""
        return self.config_data.get("mpd", self.default_config["mpd"])

    async def update_nfc_config(self, config: Dict[str, Any]) -> bool:
        """Update NFC configuration"""
        try:
            self.config_data["nfc"] = {**self.get_nfc_config(), **config}
            await self.save()
            logger.info("NFC configuration updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update NFC config: {e}")
            return False

    async def update_audio_config(self, config: Dict[str, Any]) -> bool:
        """Update audio configuration"""
        try:
            self.config_data["audio"] = {**self.get_audio_config(), **config}
            await self.save()
            logger.info("Audio configuration updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update audio config: {e}")
            return False

    def _validate_audio_source(self, audio_source: str) -> bool:
        """Validate audio source format"""
        if not audio_source:
            return False

        # Check if it's a URL
        if audio_source.startswith(("http://", "https://")):
            return True

        # Add more validation as needed
        return False

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "config_path": str(self.config_path),
            "total_cards": len(self.card_mappings),
            "nfc_config": self.get_nfc_config(),
            "audio_config": self.get_audio_config(),
            "audiobookshelf_config": {
                "base_url": self.get_audiobookshelf_config().get("base_url", ""),
                "has_credentials": bool(
                    self.get_audiobookshelf_config().get("username")
                    and self.get_audiobookshelf_config().get("password")
                ),
            },
        }
