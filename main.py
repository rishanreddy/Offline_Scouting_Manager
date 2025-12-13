# app_scout.py
from flask import Flask, render_template, request, redirect, url_for, send_file, abort, session
import csv
import datetime

from utils import load_config, append_row, get_device, get_stats, CSV_FILE, get_team_averages, get_team_info, load_all_rows, get_team_averages_as_dict, get_data_by_team, get_team_comparison_metrics

app = Flask(__name__)
app.secret_key = "offline-scouting-secret-key"  # Change this to a secure key in production


# --- Flask routes ---


@app.route("/", methods=["GET"])
def show_form():
    """Render the scouting form page (Scouting tab)."""
    device_cfg, event, fields = load_config()
    stats = get_stats()

    device_name = device_cfg.get("name") or device_cfg.get("uniqueId")
    data_path = str(CSV_FILE.resolve())

    return render_template(
        "index.html",
        event=event,
        fields=fields,
        stats=stats,
        device_name=device_name,
        data_path=data_path,
    )


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """
    Simple analysis page:
    - User uploads one or more CSV files.
    - We merge them and show every row in a big table.
    - Columns are built from uploaded CSV headers.
    - Data is stored in session to persist when navigating back.
    """
    device_cfg, event, _ = load_config()
    device_name = device_cfg.get("name") or device_cfg.get("uniqueId")

    table_columns = []
    table_rows = []
    team_averages = []
    error = None
    uploaded_filenames = []

    if request.method == "POST":
        files = request.files.getlist("csv_files")

        if not files or all(not f.filename for f in files):
            error = "Please choose at least one CSV file."
        else:
            combined_rows = []

            for f in files:
                if not f.filename:
                    continue
                uploaded_filenames.append(f.filename)
                try:
                    content = f.read().decode("utf-8-sig")
                    lines = content.splitlines()
                    reader = csv.DictReader(lines)
                    for row in reader:
                        combined_rows.append(row)
                except Exception as exc:
                    error = f"Error reading {f.filename}: {exc}"
                    combined_rows = []
                    uploaded_filenames = []
                    break

            if combined_rows and not error:
                # Build columns from CSV headers dynamically
                if combined_rows:
                    headers = list(combined_rows[0].keys())
                    table_columns = [
                        {"id": header, "label": header} for header in headers
                    ]

                table_rows = combined_rows
                # Calculate team averages
                team_averages = get_team_averages(combined_rows)
                
                # Store in session for persistence
                session["table_rows"] = combined_rows
                session["table_columns"] = table_columns
                session["team_averages"] = team_averages
                session["uploaded_filenames"] = uploaded_filenames
                session.modified = True
    else:
        # Check if we have data in session (e.g., returning from team_info)
        if "table_rows" in session:
            table_rows = session.get("table_rows", [])
            table_columns = session.get("table_columns", [])
            team_averages = session.get("team_averages", [])
            uploaded_filenames = session.get("uploaded_filenames", [])

    return render_template(
        "analyze.html",
        event=event,
        device_name=device_name,
        table_columns=table_columns,
        table_rows=table_rows,
        team_averages=team_averages,
        error=error,
        uploaded_filenames=uploaded_filenames,
    )


@app.route("/sync", methods=["GET"])
def download_sync():
    """
    Let the user download the current CSV file.
    They can save it onto a USB drive via the browser's Save dialog.
    """
    device_cfg, _, _ = load_config()
    device_id, device_name = get_device(device_cfg)

    if not CSV_FILE.exists():
        abort(404, description="No data file found yet.")

    # Build a useful filename
    safe_name = (device_name or device_id or "device").replace(" ", "_")
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"scouting_{safe_name}_{ts}.csv"

    return send_file(
        CSV_FILE,
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv",
    )


@app.route("/team_info", methods=["GET"])
def team_info():
    """
    Display detailed information for a specific team.
    Query parameter: team (team number/name)
    """
    team = request.args.get("team", "")
    
    if not team:
        return "Team not specified", 400
    
    device_cfg, event, fields = load_config()
    device_name = device_cfg.get("name") or device_cfg.get("uniqueId")
    
    # Get data from session (populated from analyze page)
    # Fall back to loading from CSV if session is empty
    all_rows = session.get("table_rows", [])
    if not all_rows:
        all_rows = load_all_rows()
    
    team_data = get_team_info(team, all_rows)
    
    return render_template(
        "team_info.html",
        team=team,
        event=event,
        device_name=device_name,
        team_data=team_data,
        fields=fields,
        team_avgs=get_team_averages_as_dict(team, all_rows),
        team_matches=get_data_by_team(team, all_rows),
        team_comps=get_team_comparison_metrics(team, all_rows, fields)
    )


@app.route("/submit", methods=["POST"])
def submit_form():
    """Handle form submission and save to CSV."""
    device_cfg, event, fields = load_config()

    # Basic required-field check
    missing = []
    for field in fields:
        if field.get("required") and not request.form.get(field["name"]):
            missing.append(field["label"])

    if missing:
        # Simple error for now (you can replace with a nicer template later)
        return f"Missing required fields: {', '.join(missing)}", 400

    append_row(device_cfg, event, fields, request.form)

    # After saving, go back to the Scouting tab
    return redirect(url_for("show_form", success="1"))


@app.route("/reset", methods=["POST"])
def reset_data():
    """Delete the local CSV so this device starts fresh."""
    if CSV_FILE.exists():
        CSV_FILE.unlink()

    return redirect(url_for("show_form", reset="1"))


if __name__ == "__main__":
    import sys

    # Check for --production flag
    production_mode = "--production" in sys.argv
    if production_mode:
        from waitress import serve

        print("Starting in production mode (Waitress)...")
        print("Serving on http://127.0.0.1:8080")
        serve(app, host="0.0.0.0", port=8080)
    else:
        print("Starting in development mode (Flask)...")
        app.run(debug=True, host="127.0.0.1", port=5000)
