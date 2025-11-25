#!/usr/bin/env python3
"""
Test script for MPD discovery service
Demonstrates automatic MPD server selection
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.mpd_discovery import MPDDiscovery, MPDConnectionManager
from config.manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_mpd_discovery():
    """Test MPD discovery functionality"""
    print("🎵 MPD Discovery Test")
    print("=" * 50)

    # Initialize config manager
    config_manager = ConfigManager()
    await config_manager.load()

    # Initialize MPD discovery
    discovery = MPDDiscovery(config_manager)

    print("\n📡 Discovering MPD servers...")
    servers = discovery.get_server_list()
    print(f"Checking servers: {servers}")

    # Discover best server
    best_server = await discovery.discover_best_server()

    if best_server:
        print(f"\n✅ Best server found:")
        print(f"   Host: {best_server.host}")
        print(f"   Port: {best_server.port}")
        print(f"   Response time: {best_server.response_time:.3f}s")
        print(f"   Version: {best_server.version}")
        print(f"   Available: {best_server.available}")
    else:
        print("\n❌ No MPD servers available")
        return

    # Test connection manager
    print(f"\n🔗 Testing connection manager...")
    connection_manager = MPDConnectionManager(discovery)

    try:
        client = await connection_manager.get_connection()
        print(f"✅ Connected to MPD successfully")

        # Test basic MPD commands
        status = client.status()
        print(f"📊 MPD Status: {status.get('state', 'unknown')}")
        print(f"🔊 Volume: {status.get('volume', '0')}%")

        # Close connection
        await connection_manager.close_connection()
        print("🔌 Connection closed")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

    # Show discovery status
    print(f"\n📈 Discovery Status:")
    status = await discovery.get_status()
    print(f"   Current server: {status['current_server']}")
    print(f"   Servers checked: {status['checked_servers']}")
    print(f"   Check interval: {status['check_interval']}s")


async def test_server_failover():
    """Test MPD server failover"""
    print("\n🔄 Testing MPD Failover")
    print("=" * 50)

    config_manager = ConfigManager()
    await config_manager.load()

    discovery = MPDDiscovery(config_manager)
    connection_manager = MPDConnectionManager(discovery)

    # Add some test servers
    discovery.add_server("localhost", 6600)
    discovery.add_server("radio", 6600)
    discovery.add_server("nonexistent", 6600)

    print("📡 Testing multiple servers...")

    # Get connection (should pick best available)
    try:
        client = await connection_manager.get_connection()
        server = await discovery.get_server()

        if server:
            print(f"✅ Connected to: {server.host}:{server.port}")
            print(f"⚡ Response time: {server.response_time:.3f}s")

        await connection_manager.close_connection()

    except Exception as e:
        print(f"❌ All servers failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_mpd_discovery())
        asyncio.run(test_server_failover())
        print("\n🎉 MPD Discovery test completed!")

    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        sys.exit(1)
