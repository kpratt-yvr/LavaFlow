#!/usr/bin/env python3
"""LavaFlow — Apple Notes → Obsidian nightly sync."""

import json
import logging
import re
import subprocess
from pathlib import Path

# --- Configure these paths for your setup ---
VAULT_DIR = Path.home() / "Documents" / "YourVaultName" / "Apple Notes"
STATE_FILE = Path.home() / ".lavaflow_state.json"
LOG_FILE = Path.home() / "Library" / "Logs" / "lavaflow.log"
# --------------------------------------------

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# Fetch all note IDs and their modification timestamps in one AppleScript call.
# Dates are formatted as ISO 8601 inside AppleScript to avoid locale-dependent parsing.
LIST_NOTES_SCRIPT = """
tell application "Notes"
    set output to ""
    repeat with aNote in every note
        set noteID to id of aNote
        set d to modification date of aNote
        set yr to year of d as string
        set mo to text -2 thru -1 of ("0" & (month of d as integer) as string)
        set dy to text -2 thru -1 of ("0" & (day of d) as string)
        set hr to text -2 thru -1 of ("0" & (hours of d) as string)
        set mi to text -2 thru -1 of ("0" & (minutes of d) as string)
        set sc to text -2 thru -1 of ("0" & (seconds of d) as string)
        set modDate to yr & "-" & mo & "-" & dy & "T" & hr & ":" & mi & ":" & sc
        set output to output & noteID & "|||" & modDate & ASCII character 10
    end repeat
    return output
end tell
"""


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def list_notes() -> list[tuple[str, str]]:
    raw = run_applescript(LIST_NOTES_SCRIPT)
    notes = []
    for line in raw.splitlines():
        line = line.strip()
        if "|||" in line:
            note_id, mod_date = line.split("|||", 1)
            notes.append((note_id.strip(), mod_date.strip()))
    return notes


def fetch_note(note_id: str) -> dict:
    safe_id = note_id.replace('"', '\\"')
    # Fields are joined with ||ANFS|| and split with maxsplit=4 so the body
    # (which can contain arbitrary text) is always the last element.
    script = f'''tell application "Notes"
    set aNote to note id "{safe_id}"
    set noteTitle to name of aNote
    set noteBody to plaintext of aNote
    set dc to creation date of aNote
    set dm to modification date of aNote
    set createdDate to (year of dc as string) & "-" & text -2 thru -1 of ("0" & (month of dc as integer) as string) & "-" & text -2 thru -1 of ("0" & (day of dc) as string)
    set modifiedDate to (year of dm as string) & "-" & text -2 thru -1 of ("0" & (month of dm as integer) as string) & "-" & text -2 thru -1 of ("0" & (day of dm) as string)
    try
        set noteFolder to name of container of aNote
    on error
        set noteFolder to "Notes"
    end try
    return noteTitle & "||ANFS||" & createdDate & "||ANFS||" & modifiedDate & "||ANFS||" & noteFolder & "||ANFS||" & noteBody
end tell'''
    raw = run_applescript(script)
    parts = raw.split("||ANFS||", 4)
    if len(parts) < 5:
        raise ValueError(f"Unexpected format from AppleScript: {raw[:80]}")
    return {
        "title": parts[0],
        "created": parts[1],
        "modified": parts[2],
        "folder": parts[3],
        "body": parts[4],
    }


def sanitize_filename(title: str) -> str:
    safe = re.sub(r'[/\\:*?"<>|]', "-", title)
    safe = safe.strip(". ")
    return (safe[:200] or "Untitled") + ".md"


def write_note_file(note: dict, filepath: Path) -> None:
    content = (
        f"---\n"
        f"created: {note['created']}\n"
        f"modified: {note['modified']}\n"
        f"source: Apple Notes\n"
        f"folder: {note['folder']}\n"
        f"---\n\n"
        f"# {note['title']}\n\n"
        f"{note['body']}\n"
    )
    filepath.write_text(content, encoding="utf-8")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"notes": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main() -> None:
    log.info("LavaFlow sync started")
    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    notes_state = state.setdefault("notes", {})

    try:
        all_notes = list_notes()
    except Exception as e:
        log.error("Failed to list notes: %s", e)
        return

    synced = skipped = errors = 0

    for note_id, mod_date in all_notes:
        stored = notes_state.get(note_id, {})
        if stored.get("modified") == mod_date:
            skipped += 1
            continue

        try:
            note = fetch_note(note_id)
        except Exception as e:
            log.error("Failed to fetch note %s: %s", note_id, e)
            errors += 1
            continue

        filename = sanitize_filename(note["title"])

        old_filename = stored.get("filename")
        if old_filename and old_filename != filename:
            old_path = VAULT_DIR / old_filename
            if old_path.exists():
                old_path.unlink()
                log.info("Removed old file after title rename: %s", old_filename)

        try:
            write_note_file(note, VAULT_DIR / filename)
        except Exception as e:
            log.error("Failed to write %s: %s", filename, e)
            errors += 1
            continue

        notes_state[note_id] = {"modified": mod_date, "filename": filename}
        log.info("Synced: %s", filename)
        synced += 1

    save_state(state)
    log.info("Done — synced: %d, skipped: %d, errors: %d", synced, skipped, errors)
    print(f"Done — synced: {synced}, skipped: {skipped}, errors: {errors}")


if __name__ == "__main__":
    main()
