"""
MPD Discovery Service for Smart Radio
Automatically discovers and selects the best MPD server
"""

import asyncio
import socket
import time
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MPDServer:
    """MPD server information"""

    host: str
    port: int
    response_time: float
    available: bool
    version: Optional[str] = None


class MPDDiscovery:
    """Discovers and selects the best MPD server"""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.current_server: Optional[MPDServer] = None
        self.last_check_time: float = 0

        # Get configuration
        if config_manager:
            mpd_config = config_manager.get_mpd_config()
            self.timeout = mpd_config.get("discovery_timeout", 3.0)
            self.check_interval = mpd_config.get("check_interval", 30.0)
            servers_config = mpd_config.get("servers", [])
        else:
            self.timeout = 3.0
            self.check_interval = 30.0
            servers_config = []

        # Default MPD servers to check
        default_servers = [
            ("localhost", 6600),  # Local MPD
            ("radio", 6600),  # Remote MPD server
        ]

        # Convert config to tuples and add defaults
        self.mpd_servers = []
        for server in servers_config:
            self.mpd_servers.append((server["host"], server["port"]))

        # Add defaults if not already present
        for server in default_servers:
            if server not in self.mpd_servers:
                self.mpd_servers.append(server)

    async def discover_best_server(self) -> Optional[MPDServer]:
        """Discover the best available MPD server"""
        logger.info("Discovering MPD servers...")

        tasks = []
        for host, port in self.mpd_servers:
            task = asyncio.create_task(self._ping_server(host, port))
            tasks.append(task)

        # Ping all servers concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results and find the fastest
        available_servers = []
        for result in results:
            if isinstance(result, MPDServer) and result.available:
                available_servers.append(result)

        if not available_servers:
            logger.warning("No MPD servers are available")
            return None

        # Sort by response time (fastest first)
        best_server = min(available_servers, key=lambda s: s.response_time)

        logger.info(
            f"Selected MPD server: {best_server.host}:{best_server.port} "
            f"(response time: {best_server.response_time:.3f}s, "
            f"version: {best_server.version})"
        )

        return best_server

    async def _ping_server(self, host: str, port: int) -> MPDServer:
        """Ping a specific MPD server"""
        start_time = time.time()

        try:
            # Create socket connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=self.timeout
            )

            response_time = time.time() - start_time

            # Send MPD hello command (just connect is enough to check availability)
            try:
                # Read the MPD welcome message
                data = await asyncio.wait_for(reader.readuntil(b"\n"), timeout=2.0)
                welcome_msg = data.decode("utf-8").strip()

                # Extract MPD version from welcome message
                version = None
                if welcome_msg.startswith("OK MPD "):
                    version = welcome_msg[8:]

            except asyncio.TimeoutError:
                logger.warning(f"MPD {host}:{port} connected but no welcome message")
                version = "unknown"

            writer.close()
            await writer.wait_closed()

            return MPDServer(
                host=host,
                port=port,
                response_time=response_time,
                available=True,
                version=version,
            )

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.debug(f"MPD server {host}:{port} not available: {e}")
            return MPDServer(
                host=host, port=port, response_time=self.timeout, available=False
            )
        except Exception as e:
            logger.error(f"Unexpected error pinging MPD {host}:{port}: {e}")
            return MPDServer(
                host=host, port=port, response_time=self.timeout, available=False
            )

    async def get_server(self, force_check: bool = False) -> Optional[MPDServer]:
        """Get the current best MPD server, rechecking if needed"""
        current_time = time.time()

        # Check if we need to rediscover
        if (
            force_check
            or self.current_server is None
            or current_time - self.last_check_time > self.check_interval
        ):
            new_server = await self.discover_best_server()

            if new_server:
                self.current_server = new_server
                self.last_check_time = current_time
            else:
                # Keep the old server if available, even if it's not responding now
                if self.current_server is None:
                    logger.error("No MPD servers available at all")
                return None

        return self.current_server

    async def verify_connection(self, host: str, port: int) -> bool:
        """Verify if a specific MPD server is available"""
        server = await self._ping_server(host, port)
        return server.available

    def add_server(self, host: str, port: int = 6600) -> None:
        """Add a new MPD server to the discovery list"""
        server_tuple = (host, port)
        if server_tuple not in self.mpd_servers:
            self.mpd_servers.append(server_tuple)
            logger.info(f"Added MPD server to discovery list: {host}:{port}")

    def remove_server(self, host: str, port: int = 6600) -> None:
        """Remove an MPD server from the discovery list"""
        server_tuple = (host, port)
        if server_tuple in self.mpd_servers:
            self.mpd_servers.remove(server_tuple)
            logger.info(f"Removed MPD server from discovery list: {host}:{port}")

    def get_server_list(self) -> list:
        """Get the list of servers being checked"""
        return self.mpd_servers.copy()

    async def get_status(self) -> Dict[str, Any]:
        """Get current discovery status"""
        current_server = await self.get_server()

        return {
            "current_server": {
                "host": current_server.host,
                "port": current_server.port,
                "response_time": current_server.response_time,
                "version": current_server.version,
                "available": current_server.available,
            }
            if current_server
            else None,
            "checked_servers": len(self.mpd_servers),
            "last_check_time": self.last_check_time,
            "check_interval": self.check_interval,
            "servers_to_check": self.mpd_servers,
        }


class MPDConnectionManager:
    """Manages MPD connection with automatic failover"""

    def __init__(self, discovery: MPDDiscovery):
        self.discovery = discovery
        self.current_client = None
        self.current_host = None
        self.current_port = None

    async def get_connection(self, force_rediscover: bool = False):
        """Get an MPD client connection with automatic failover"""
        try:
            import mpd

            # Get the best server
            server = await self.discovery.get_server(force_check=force_rediscover)

            if not server:
                raise Exception("No MPD servers available")

            # If we already have a connection to this server, return it
            if (
                self.current_client
                and self.current_host == server.host
                and self.current_port == server.port
            ):
                # Test if the connection is still alive
                try:
                    self.current_client.ping()
                    return self.current_client
                except:
                    # Connection is dead, close it and create a new one
                    try:
                        self.current_client.close()
                    except:
                        pass
                    self.current_client = None

            # Create new connection
            client = mpd.MPDClient()
            client.timeout = 10
            client.idletimeout = None

            client.connect(server.host, server.port)

            self.current_client = client
            self.current_host = server.host
            self.current_port = server.port

            logger.info(f"Connected to MPD at {server.host}:{server.port}")
            return client

        except Exception as e:
            logger.error(f"Failed to connect to MPD: {e}")
            raise

    async def close_connection(self) -> None:
        """Close the current MPD connection"""
        if self.current_client:
            try:
                self.current_client.close()
                logger.info("Closed MPD connection")
            except Exception as e:
                logger.warning(f"Error closing MPD connection: {e}")
            finally:
                self.current_client = None
                self.current_host = None
                self.current_port = None
