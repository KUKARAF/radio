# Change: Add NFC-based Smart Radio System

## Why
Enable users to play radio streams and podcasts by simply tapping NFC cards, providing an intuitive physical interface for audio playback without requiring complex UI interactions.

## What Changes
- Add NFC scanner integration for Raspberry Pi GPIO pins 7 and 11
- Implement audio playback system for radio streams and podcasts
- Create systemd service for continuous NFC monitoring
- Add configuration system for mapping NFC cards to audio sources
- Implement state machine for audio playback control
- Add error handling and recovery mechanisms

## Impact
- Affected specs: New capabilities for `audio-playback` and `nfc-interaction`
- Affected code: Core application logic, hardware interfaces, systemd service configuration
- Hardware dependencies: NFC scanner module, Raspberry Pi GPIO, audio output
- External dependencies: Radio streaming servers, Audiobookshelf instances