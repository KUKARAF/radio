#!/usr/bin/env python3
"""
Simple status page for smart radio service
Shows current service status and allows basic control
"""

import asyncio
import json
from aiohttp import web
from nfc.scanner import NFCScanner
from playback.manager import PlaybackManager
from config.manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


class StatusServer:
    """Simple web server for smart radio status"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.nfc_scanner = NFCScanner()
        self.playback_manager = PlaybackManager(self.config_manager)
        self.status = "unknown"

    async def get_service_status(self):
        """Get current service status"""
        try:
            # Check if service components are working
            mpd_status = (
                await self.playback_manager.get_status()
                if self.playback_manager
                else {"state": "unknown"}
            )
            nfc_status = (
                "ready"
                if self.nfc_scanner and self.nfc_scanner.state.value == "ready"
                else "not_ready"
            )

            self.status = {
                "service": "smart_radio",
                "mpd": {
                    "connected": mpd_status.get("state") != "unknown",
                    "server": mpd_status.get("current_player", "unknown"),
                    "volume": mpd_status.get("volume", 0.5),
                },
                "nfc": {"status": nfc_status, "gpio_pins": {"sda": 2, "scl": 3}},
                "timestamp": asyncio.get_event_loop().time(),
            }

            return self.status

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {"service": "smart_radio", "error": str(e)}

    async def handle_status_request(self, request):
        """Handle status requests"""
        if request.path == "/status":
            status = await self.get_service_status()
            return web.Response(
                text=json.dumps(status, indent=2), content_type="application/json"
            )

        return web.Response(text="Not Found", status=404)

    async def handle_root(self, request):
        """Handle root requests"""
        status = await self.get_service_status()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Smart Radio Status</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; color: #333; margin-bottom: 20px; }}
                .status {{ padding: 15px; border-radius: 5px; }}
                .status-item {{ margin: 10px 0; padding: 10px; border-radius: 3px; }}
                .status-working {{ background: #28a745; color: white; }}
                .status-error {{ background: #dc3545; color: white; }}
                .status-unknown {{ background: #6c757d; color: white; }}
                h2 {{ margin: 0 0 10px 0; color: #333; }}
                .value {{ font-size: 1.2em; font-weight: bold; }}
                .label {{ font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎵 Smart Radio Status</h1>
                    <p>NFC-based Audio Playback System</p>
                </div>
                
                <div class="status">
                    <h2>System Status</h2>
                    
                    <div class="status-item">
                        <h3>🎵 MPD Audio Service</h3>
                        <div class="status-working">
                            ✅ Connected: <span class="value">{mpd_status.get("server", "unknown")}</span>
                        </div>
                        <div class="status-working">
                            ✅ Volume: <span class="value">{mpd_status.get("volume", 0.5) * 100}%</span>
                        </div>
                        <div class="status-working">
                            ✅ State: <span class="value">{mpd_status.get("state", "unknown")}</span>
                        </div>
                    </div>
                    
                    <div class="status-item">
                        <h3>📡 NFC Scanner</h3>
                        <div class="status-working">
                            ✅ Status: <span class="value">{nfc_status}</span>
                        </div>
                        <div class="status-working">
                            ✅ GPIO Pins: <span class="value">SDA=2, SCL=3</span>
                        </div>
                    </div>
                    
                    <div class="status-item">
                        <h3>⏰ Last Updated</h3>
                        <div class="status-working">
                            <span class="value">{status.get("timestamp", "unknown")}</span>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return web.Response(text=html, content_type="text/html")

    def setup_routes(self):
        """Setup web routes"""
        self.app = web.Application()
        self.app.router.add_get("/status", self.handle_status_request)
        self.app.router.add_get("/", self.handle_root)


async def main():
    """Main entry point for status server"""
    server = StatusServer()

    # Setup routes
    server.setup_routes()

    runner = web.AppRunner(host="0.0.0.0", port=8080)
    await runner.setup()

    logger.info("Smart Radio Status Server started on http://0.0.0.0:8080")

    try:
        await runner.serve()
    except KeyboardInterrupt:
        logger.info("Status server stopped")
    except Exception as e:
        logger.error(f"Status server error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
