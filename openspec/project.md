# Project Context

## Purpose
A smart radio system that plays radio streams and podcasts through NFC interaction. Users can tap NFC cards to immediately play audio sources without complex interfaces. The system runs on DietPi OS with Allo.com Web GUI on a Raspberry Pi with NFC scanner hardware on pins 7 and 11, leveraging the existing audiophile software stack for high-quality audio playback.

## Tech Stack
- **DietPi OS** - Lightweight Linux distribution optimized for audio applications
- **Allo.com Web GUI** - Web-based system configuration and control interface
- **Python 3.11+** - Primary programming language
- **uv** - Python package manager and virtual environment tool
- **systemd** - Service management for Linux
- **Raspberry Pi** - Target hardware platform
- **NFC Scanner** - Hardware interface on GPIO pins 7 and 11
- **Audio libraries** - For streaming radio and podcast playback
- **Audiophile software stack**: Roon Bridge, MPD/O!MPD, Shairport-sync (AirPlay), Squeezelite, GMediaRender (DLNA)


## Project Conventions

### Code Style
- Follow PEP 8 Python style guidelines
- Use type hints throughout the codebase
- Maximum line length: 88 characters (Black formatter default)
- Use descriptive variable and function names
- Docstrings for all public functions and classes

### Architecture Patterns
- **Service-oriented architecture** with systemd-managed services
- **Event-driven design** for NFC interactions
- **State machine pattern** for audio playback control
- **Configuration-driven** for audio source management
- **Hardware abstraction layer** for NFC scanner interface
- **Web-based management** through Allo.com GUI for system configuration
- **Multi-protocol audio support** (Roon, AirPlay, DLNA, MPD)



### Testing Strategy
- Unit tests with pytest for core logic
- Integration tests for NFC hardware interaction
- Mock hardware interfaces for CI/CD testing
- Manual testing on actual Raspberry Pi hardware

### Git Workflow
- Feature branches for new capabilities
- Descriptive commit messages with conventional commits
- Main branch reflects production-ready state
- Tags for releases

## Domain Context

### Audio Sources
- **Radio streams**: HTTP streaming URLs (e.g., https://streaming.radiostreamlive.com/radiolovelive_devices)
- **Podcasts**: Remote Audiobookshelf server at audiobooks.osmosis.page (e.g., https://audiobooks.osmosis.page/audiobookshelf/item/9a920e27-e6b2-43cb-a112-00c1f3381758)

### NFC Interaction Model
- Each NFC card maps to a specific audio source
- Tap-to-play interaction model
- Immediate audio playback upon successful NFC read
- No UI required for basic operation

### Hardware Interface
- NFC scanner connected to GPIO pins 7 and 11
- Continuous monitoring for NFC card presence
- Debouncing to prevent multiple reads from single tap

## Important Constraints

### Hardware Constraints
- Raspberry Pi resource limitations (CPU, memory)
- GPIO pin availability and electrical specifications
- Audio output hardware compatibility
- Network connectivity for streaming sources

### Performance Constraints
- Fast NFC response time (< 500ms from tap to audio)
- Stable streaming without buffering interruptions
- Low system resource usage for 24/7 operation

### Reliability Constraints
- System must auto-recover from failures
- Graceful handling of network interruptions
- Hardware fault detection and reporting

## External Dependencies

### Hardware Dependencies
- NFC scanner module (PN532 or compatible)
- Raspberry Pi 4 with GPIO access
- Audio output hardware (speakers/headphones)
- Network interface (Ethernet recommended for stable streaming)

### Software Dependencies
- Linux system with systemd
- DietPi OS with Allo.com Web GUI
- Python 3.11+ runtime
- Network connectivity for streaming
- Audio system (PulseAudio/ALSA)
- Samba Server for file/music transfer
- NetData for system monitoring
- Roon Bridge, MPD/O!MPD, Shairport-sync, Squeezelite, GMediaRender

### Network Dependencies
- Radio streaming servers
- Remote Audiobookshelf server at audiobooks.osmosis.page
- DNS resolution for streaming URLs
- Tailscale MDNS for hostname resolution (radio)
