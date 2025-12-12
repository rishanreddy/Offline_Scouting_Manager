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
        graph: none
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

def get_data_by_team(team_number: int, data):
    """Filter CSV data for a specific team number."""
    team_str = str(team_number)
    get_data_by_team(team_str, data)

def get_data_by_team(team_number: str, data):
    """Filter CSV data for a specific team number."""
    filtered = [row for row in data if row.get("team") == team_number]
    return filtered

def get_team_averages_as_dict(team: str, data):
    fdata = get_data_by_team(team, data)

    averages = {}
    non_numbers = {}

    for row in fdata:
        for key, value in row.items():
            try:
                iv = int(value)
            except:
                non_numbers[key] = value
            else:
                if key not in averages:
                    averages[key] = {"total": 0, "count": 0}
                averages[key]["total"] += iv
                averages[key]["count"] += 1
    
    result = {}
    for key, value in averages.items():
        result[key] = round(value["total"] / value["count"], 2)

    return result | non_numbers

def get_team_comparison_metrics(team: str, data, fields):
    """
    Compare a team's metrics to the best performing team in each numeric field.
    
    Returns a dictionary with:
      - field_name: percent of best score (e.g., 80 means 80% of best)
    
    Only includes fields that have graphs (i.e., numeric fields).
    """
    if not data:
        return {}
    
    # Get this team's averages
    team_averages = get_team_averages_as_dict(team, data)
    
    # Get all unique teams in the dataset
    all_teams = set()
    for row in data:
        team_val = row.get("team")
        if team_val:
            all_teams.add(team_val)
    
    # Find the best (max) average for each numeric field
    best_averages = {}
    for field_name in team_averages.keys():
        best_value = 0
        for other_team in all_teams:
            try:
                other_avg = get_team_averages_as_dict(str(other_team), data)
                if field_name in other_avg:
                    for field in fields:
                        if field["name"] == field_name and field.get("graph") != "none":
                            value = float(other_avg[field_name])
                            if value > best_value:
                                best_value = value
            except (ValueError, TypeError):
                pass
        best_averages[field_name] = best_value
    
    # Calculate percentages of best score
    result = {}
    for field_name, team_value in team_averages.items():
        if field_name in best_averages and best_averages[field_name] > 0:
            try:
                team_val = float(team_value)
                best_val = best_averages[field_name]
                percent = round((team_val / best_val) * 100, 2)
                result[field_name] = percent
            except (ValueError, TypeError):
                pass
    
    return result

def get_team_averages(rows):
    """
    Calculate average scores for each team by summing teleop and auto scores.
    
    Returns a list of dicts with:
      - team: team number/name
      - entry_count: number of entries for this team
      - avg_score: average of (teleop + auto) per entry
    
    Dynamically finds columns containing 'teleop' and 'auto' (case-insensitive).
    """
    if not rows:
        return []
    
    # Find teleop and auto score column names
    first_row = rows[0]
    teleop_col = None
    auto_col = None
    team_col = None
    
    for col_name in first_row.keys():
        col_lower = col_name.lower()
        if 'teleop' in col_lower and not teleop_col:
            teleop_col = col_name
        if 'auto' in col_lower and not auto_col:
            auto_col = col_name
        if col_lower == 'team' or col_lower == 'team_number':
            team_col = col_name
    
    # If we can't find the columns, return empty
    if not teleop_col or not auto_col or not team_col:
        return []
    
    # Group by team and calculate averages
    team_data = {}
    for row in rows:
        team = row.get(team_col, "Unknown")
        if not team:
            continue
        
        try:
            teleop_score = float(row.get(teleop_col, 0) or 0)
            auto_score = float(row.get(auto_col, 0) or 0)
            combined_score = teleop_score + auto_score
        except (ValueError, TypeError):
            continue
        
        if team not in team_data:
            team_data[team] = {"scores": [], "count": 0}
        
        team_data[team]["scores"].append(combined_score)
        team_data[team]["count"] += 1
    
    # Calculate averages and sort by team
    result = []
    for team, data in sorted(team_data.items()):
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        result.append({
            "team": team,
            "entry_count": data["count"],
            "avg_score": round(avg_score, 2),
        })
    
    return result


def get_team_info(team_number, rows):
    """
    Get detailed information for a specific team.
    
    Returns a dict with:
      - team: team number
      - total_entries: total number of entries
      - avg_auto_score: average auto score
      - avg_teleop_score: average teleop score
      - avg_combined_score: average combined score
      - records: list of match records for this team (with original field names)
    """
    if not rows:
        return {
            "team": team_number,
            "total_entries": 0,
            "avg_auto_score": 0,
            "avg_teleop_score": 0,
            "avg_combined_score": 0,
            "records": [],
        }
    
    # Find column names dynamically
    first_row = rows[0]
    team_col = None
    teleop_col = None
    auto_col = None
    
    for col_name in first_row.keys():
        col_lower = col_name.lower()
        if col_lower == 'team' or col_lower == 'team_number':
            team_col = col_name
        if 'teleop' in col_lower and not teleop_col:
            teleop_col = col_name
        if 'auto' in col_lower and not auto_col:
            auto_col = col_name
    
    if not team_col:
        return {
            "team": team_number,
            "total_entries": 0,
            "avg_auto_score": 0,
            "avg_teleop_score": 0,
            "avg_combined_score": 0,
            "records": [],
        }
    
    # Filter rows for this team
    team_str = str(team_number)
    team_rows = [row for row in rows if str(row.get(team_col, "")) == team_str]
    
    if not team_rows:
        return {
            "team": team_number,
            "total_entries": 0,
            "avg_auto_score": 0,
            "avg_teleop_score": 0,
            "avg_combined_score": 0,
            "records": [],
        }
    
    # Calculate averages
    auto_scores = []
    teleop_scores = []
    
    for row in team_rows:
        try:
            auto_score = float(row.get(auto_col, 0) or 0) if auto_col else 0
            teleop_score = float(row.get(teleop_col, 0) or 0) if teleop_col else 0
            auto_scores.append(auto_score)
            teleop_scores.append(teleop_score)
        except (ValueError, TypeError):
            continue
    
    avg_auto = sum(auto_scores) / len(auto_scores) if auto_scores else 0
    avg_teleop = sum(teleop_scores) / len(teleop_scores) if teleop_scores else 0
    avg_combined = avg_auto + avg_teleop
    
    # Build records list - keep original field names from CSV
    records = []
    for row in team_rows:
        # Create record with all fields except team
        record = {}
        for key, value in row.items():
            if key.lower() != 'team' and key.lower() != 'team_number':
                record[key] = value
        records.append(record)
    
    return {
        "team": team_number,
        "total_entries": len(team_rows),
        "avg_auto_score": round(avg_auto, 2),
        "avg_teleop_score": round(avg_teleop, 2),
        "avg_combined_score": round(avg_combined, 2),
        "records": records,
    }