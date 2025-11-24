## Context
Building a smart radio system that runs on Raspberry Pi with NFC interaction as the primary interface. The system needs to be reliable for 24/7 operation, respond quickly to NFC interactions, and handle various audio sources including radio streams and podcasts.

## Goals / Non-Goals
- Goals: 
  - Instant audio playback upon NFC tap (< 500ms response time)
  - Reliable 24/7 operation with auto-recovery
  - Support for radio streams and Audiobookshelf podcasts
  - Simple configuration for NFC card mappings
- Non-Goals:
  - Complex UI or mobile app
  - Multi-room audio synchronization
  - Voice control integration
  - Music library management

## Decisions
- Decision: Use Python with uv for package management
  - Rationale: Python has excellent hardware libraries (GPIO, NFC, audio), uv provides fast dependency management
  - Alternatives considered: Node.js (limited hardware support), Go (complex audio libraries), C++ (overkill for this scope)

- Decision: systemd service for process management
  - Rationale: Native Linux service management, automatic restart on failure, standard for Raspberry Pi
  - Alternatives considered: Docker (overhead), custom daemon (reinventing systemd)

- Decision: Event-driven architecture with state machine
  - Rationale: Clean separation of concerns, predictable behavior, easy testing
  - Alternatives considered: Simple linear script (hard to maintain), callback hell (complex debugging)

- Decision: Configuration file for NFC-to-audio mappings
  - Rationale: Easy to modify without code changes, user-friendly
  - Alternatives considered: Database (overkill), hardcoded mappings (inflexible)

## Risks / Trade-offs
- Hardware failure risk → Mitigation: Health monitoring, error logging, graceful degradation
- Network interruption risk → Mitigation: Buffering, retry logic, offline detection
- GPIO conflict risk → Mitigation: Pin documentation, configuration validation
- Audio latency risk → Mitigation: Optimized libraries, buffering strategy

## Migration Plan
1. Set up development environment with Python and uv
2. Implement NFC scanner interface with mock hardware
3. Create audio playback subsystem with test streams
4. Integrate NFC and audio components
5. Add systemd service configuration
6. Deploy to Raspberry Pi for hardware testing
7. Configure production NFC cards and audio sources

## Open Questions
- Specific NFC scanner model compatibility (PN532 assumed)
- Audio system preference (PulseAudio vs ALSA)
- Configuration format (YAML vs JSON vs TOML)
- Logging verbosity and rotation strategy
- Network connectivity monitoring approach