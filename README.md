# Offline Scouting Manager

A Flask web app for robotics competition scouting that works completely offline. Built for FTC/FRC teams who need to collect match data on devices without internet access.

## What it does

- **Collect data**: Custom forms for recording match observations
- **Sync between devices**: Export/import CSV files via USB
- **Analyze results**: View and filter all scouting data in one place
- **Works offline**: No internet required

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first:

Then:

```bash
# Install dependencies
uv sync

# Run the app
uv run main.py
```

**Alternative**: Run `setup-run.bat` (Windows) to automatically install dependencies and start the app.

Open `http://127.0.0.1:5000` in your browser.

## Configuration

Edit `config/config.yaml` to customize:

- Event name and season
- Device identification
- Form fields and data types

Each device should have a unique ID in `config/device.json` that is automatically generated using the device idenification (so make sure you give each device that will be scouting a unique name).

## Usage

1. Fill out scouting forms during matches
2. Data saves to `data/scouting_data.csv`
3. Export CSV to USB drive
4. Import CSVs from all scouting devices on the Analysis page
5. View combined data from all scouts

## Tech Stack

- Flask + Jinja2
- Tailwind CSS + Flowbite
- DataTables for sorting/filtering
- YAML for config
