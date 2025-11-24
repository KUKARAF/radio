## ADDED Requirements

### Requirement: Radio Stream Playback
The system SHALL play internet radio streams from HTTP streaming URLs.

#### Scenario: Successful radio stream playback
- **WHEN** a valid radio stream URL is provided
- **THEN** the system SHALL begin audio playback within 2 seconds
- **AND** the stream SHALL continue playing without interruption

#### Scenario: Radio stream connection failure
- **WHEN** the radio stream URL is unreachable
- **THEN** the system SHALL log the error
- **AND** attempt reconnection up to 3 times with 5-second intervals
- **AND** notify the user of playback failure after final attempt

#### Scenario: Radio stream buffering
- **WHEN** network latency causes buffering
- **THEN** the system SHALL maintain audio playback with minimal interruption
- **AND** implement adaptive buffering to prevent stuttering

### Requirement: Podcast Playback
The system SHALL play podcast episodes from Audiobookshelf instances.

#### Scenario: Successful podcast playback
- **WHEN** a valid Audiobookshelf item URL is provided
- **THEN** the system SHALL extract the audio stream URL
- **AND** begin playback within 3 seconds
- **AND** maintain playback state (position, volume)

#### Scenario: Podcast authentication
- **WHEN** the Audiobookshelf instance requires authentication
- **THEN** the system SHALL use configured credentials
- **AND** handle authentication failures gracefully

#### Scenario: Podcast episode completion
- **WHEN** a podcast episode finishes playing
- **THEN** the system SHALL stop playback cleanly
- **AND** reset the playback state
- **AND** log the completion for analytics

### Requirement: Audio Control
The system SHALL provide basic audio playback controls.

#### Scenario: Volume adjustment
- **WHEN** volume commands are issued
- **THEN** the system SHALL adjust volume smoothly
- **AND** maintain volume settings across playback sessions

#### Scenario: Playback state management
- **WHEN** playback is interrupted (new NFC card, error)
- **THEN** the system SHALL stop current playback cleanly
- **AND** release audio resources
- **AND** reset to initial state

#### Scenario: Audio output selection
- **WHEN** multiple audio outputs are available
- **THEN** the system SHALL use the configured default output
- **AND** allow output configuration via settings

### Requirement: Audio Configuration
The system SHALL support configurable audio settings.

#### Scenario: Audio source mapping
- **WHEN** configuring NFC card mappings
- **THEN** the system SHALL accept radio stream URLs
- **AND** accept Audiobookshelf item URLs
- **AND** validate URL formats before saving

#### Scenario: Audio quality settings
- **WHEN** configuring audio preferences
- **THEN** the system SHALL support bitrate selection
- **AND** support audio format preferences
- **AND** apply settings to new playback sessions