# Libretro Image Matching Server

A FastAPI-based server that matches game ROM names with their corresponding thumbnail images from the Libretro thumbnails database. This service is particularly useful for MinUI and other retro gaming interfaces that need to match ROM filenames with their corresponding box art or screenshots.

## Features

- Matches ROM filenames with Libretro thumbnails using fuzzy string matching
- Supports multiple retro gaming consoles and systems
- Returns results in both JSON and plain text formats
- Handles various ROM naming conventions and formats

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/josegonzalez/minui-image-matching-server.git
cd minui-image-matching-server
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

Run the server using uvicorn:

```bash
uvicorn main:app --reload
```

The server will start on `http://localhost:8000` by default.

### API Endpoints

#### POST /matches/{console}

Matches a list of ROM filenames with their corresponding thumbnail images.

Example request:

```bash
curl -X POST http://localhost:8000/matches/GB/snap \
  -d "Pokemon Red (USA).gb
Pokemon Blue (USA).gb"
```

The response will be in JSON format:

```json
{
  "console": "GB",
  "matches": {
    "Pokemon Red (USA).gb": "https://thumbnails.libretro.com/...",
    "Pokemon Blue (USA).gb": "https://thumbnails.libretro.com/..."
  }
}
```

Or in plain text format (when `Content-Type` is `text/plain`):

```
Pokemon Red (USA).gb    https://thumbnails.libretro.com/...
Pokemon Blue (USA).gb   https://thumbnails.libretro.com/...
```

### Supported Consoles

The server supports various retro gaming consoles and systems, including:

- Nintendo: GB, GBA, GBC, N64, NDS, FC (NES), SFC (SNES)
- Sega: MD (Genesis), SMS, DC, SATURN, GG
- Sony: PS, PSP
- And many more...

For a complete list of supported consoles, see the `rom_mapping` dictionary in the source code.

## License

This project is open source and available under the MIT License.
