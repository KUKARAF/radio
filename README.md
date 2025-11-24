# Smart Radio

NFC-based smart radio system for audio playback using RFID cards.

## Features

- NFC card detection for audio source selection
- Support for Audiobookshelf and radio streaming
- Event-driven architecture with asyncio
- GPIO-based NFC scanner integration
- Configurable card-to-audio mappings

## Installation

### Using uv (Recommended)

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone <repository-url>
cd smart-radio
```

3. Install dependencies:
```bash
uv sync
```

### Traditional Installation

```bash
pip install -e .
```

## Running the Service

### Development Mode

Run the service directly with uv:

```bash
uv run python main.py
```

Or activate the virtual environment first:

```bash
uv shell
python main.py
```

### Production Mode with systemd

1. Copy the service file to systemd:
```bash
sudo cp smart-radio.service /etc/systemd/system/
```

2. Create the application directory:
```bash
sudo mkdir -p /opt/smart-radio
sudo cp -r . /opt/smart-radio/
sudo chown -R pi:pi /opt/smart-radio
```

3. Install dependencies in production:
```bash
cd /opt/smart-radio
uv sync --frozen
```

4. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable smart-radio
sudo systemctl start smart-radio
```

5. Check service status:
```bash
sudo systemctl status smart-radio
```

6. View logs:
```bash
sudo journalctl -u smart-radio -f
```

## Configuration

The service uses configuration files in the `config/` directory. You can customize:

- NFC scanner GPIO pins
- Audio source mappings
- Playback settings
- Logging configuration

## Development

### Code Quality

Run linting and formatting:

```bash
uv run ruff check .
uv run black .
uv run mypy .
```

### Testing

```bash
uv run pytest
```

## Hardware Requirements

- Raspberry Pi (3B+ or newer recommended)
- RC522 NFC reader
- GPIO connections for NFC scanner
- Audio output device (speakers/headphones)

## License

MIT