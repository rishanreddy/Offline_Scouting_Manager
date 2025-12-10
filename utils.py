import datetime
from pathlib import Path
import csv
import uuid
import json
import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.yaml"
DEVICE_FILE = CONFIG_DIR / "device.json"
CSV_FILE = DATA_DIR / "scouting_data.csv"


def format_timestamp(ts: str | None) -> str:
    """Convert an ISO timestamp string to a human-readable format."""
    if not ts:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(ts)
    except ValueError:
        # If it isn't a valid ISO string, just show whatever it is
        return ts
    # Example: "Dec 09, 2025 02:34 PM"
    return dt.strftime("%b %d, %Y %I:%M %p")


def load_config():
    """
    Load device, event, and fields definition from config/config.yaml.

    Expected structure:

    device:
      uniqueId: "scout_device_001"
      name: "Main Scout Tablet"

    event:
      name: "Example Robotics Event"
      season: "2024-2025"
      # optional:
      # config_id: "example_v1"

    fields:
      - name: match
        label: "Match #"
        type: integer
        required: true
      ...
    """
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    device = cfg.get("device", {}) or {}
    event = cfg.get("event", {}) or {}
    fields = cfg.get("fields", []) or []

    return device, event, fields


def get_device(device_cfg):
    """
    Return (device_id, device_name) for this installation.

    device_id priority:
      1) device.uniqueId from config.yaml (if present)
      2) existing ID stored in config/device.json
      3) a new random UUID

    device_name:
      - from device.name in config.yaml if present
      - otherwise from device.json if stored there

    The chosen values are persisted back into config/device.json
    so they remain stable even if config.yaml changes later.
    """
    existing = {}
    if DEVICE_FILE.exists():
        try:
            with DEVICE_FILE.open("r", encoding="utf-8") as f:
                existing = json.load(f) or {}
        except Exception:
            existing = {}

    device_id = (
        device_cfg.get("uniqueId") or existing.get("device_id") or uuid.uuid4().hex[:12]
    )
    device_name = device_cfg.get("name") or existing.get("device_name")

    DEVICE_FILE.parent.mkdir(exist_ok=True)
    to_store = {"device_id": device_id}
    if device_name:
        to_store["device_name"] = device_name
    with DEVICE_FILE.open("w", encoding="utf-8") as f:
        json.dump(to_store, f)

    return device_id, device_name


def get_event_ids(event_cfg):
    """
    Derive (config_id, event_name, event_season) from event config.

    If event.config_id is missing, we generate one from name + season, e.g.
    "Example Robotics Event", "2024-2025" -> "example_robotics_event_2024-2025"
    """
    event_name = (event_cfg.get("name") or "").strip()
    event_season = (event_cfg.get("season") or "").strip()
    config_id = (event_cfg.get("config_id") or "").strip()

    if not config_id:
        parts = [p for p in [event_name, event_season] if p]
        if parts:
            config_id = "_".join(parts).lower().replace(" ", "_")
        else:
            config_id = "unknown_config"

    return config_id, event_name, event_season


def get_csv_header(fields):
    """
    Base columns + one column per field name from config.

    Every row is tagged with:
      - event_name, event_season, config_id
      - device_id, device_name
      - dynamic scouting fields
    """
    base_cols = [
        "timestamp",
        "event_name",
        "event_season",
        "config_id",
        "device_id",
        "device_name",
    ]
    field_cols = [f["name"] for f in fields]
    return base_cols + field_cols


def ensure_csv_header(fields):
    """If the CSV file doesn't exist, create it and write the header row."""
    if CSV_FILE.exists():
        return

    header = get_csv_header(fields)
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def cast_value(field, raw_value: str) -> str:
    """
    Convert raw form input (string) into the right type, then back to string
    for CSV. If conversion fails, keep the original string.
    """
    if raw_value is None:
        return ""

    raw_value = raw_value.strip()
    ftype = field.get("type", "text")

    if ftype == "integer":
        if raw_value == "":
            return ""
        try:
            value_int = int(raw_value)
            return str(value_int)
        except ValueError:
            # For MVP, just keep original string; you can add error handling later.
            return raw_value

    # text / select / textarea → just return stripped string
    return raw_value


def append_row(device_cfg, event_cfg, fields, form_data):
    """Append one row to the CSV file, using device + event config."""
    ensure_csv_header(fields)

    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    config_id, event_name, event_season = get_event_ids(event_cfg)
    device_id, device_name = get_device(device_cfg)

    row = {
        "timestamp": timestamp,
        "event_name": event_name,
        "event_season": event_season,
        "config_id": config_id,
        "device_id": device_id,
        "device_name": device_name or "",
    }

    for field in fields:
        name = field["name"]
        raw_value = form_data.get(name, "")
        row[name] = cast_value(field, raw_value)

    header = get_csv_header(fields)
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writerow(row)


def get_stats():
    if not CSV_FILE.exists():
        return {
            "entries": 0,
            "last_timestamp": None,
        }

    with CSV_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    entries = len(rows)
    last_ts_raw = rows[-1].get("timestamp") if rows else None

    return {
        "entries": entries,
        "last_timestamp": format_timestamp(last_ts_raw),
    }


def load_all_rows():
    """Return all CSV rows as a list of dicts."""
    if not CSV_FILE.exists():
        return []
    with CSV_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)
