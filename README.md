![Header](https://raw.githubusercontent.com/kpratt-yvr/LavaFlow/refs/heads/main/Logo.png) 
# LavaFlow

A lightweight macOS tool that syncs your Apple Notes into an Obsidian vault every night at 11:59 PM. Only new or edited notes are written in the  sync, while unchanged notes are skipped to prevent duplication. I created this, mostly because the Obsidian mobile experience is not great, while the Apple Notes experience is fast, smooth, and easy to use on the go. The key is to use Apple Notes as the entry point for mobile notes, which will be synced to an Obsidian vault nightly, ensuring they are in sync. 

## How it works

- Reads all notes from Apple Notes via AppleScript
- Compares each note's modification date against a local state file
- Writes only new or changed notes as `.md` files into your Obsidian vault
- Adds YAML frontmatter with `created`, `modified`, `source`, and `folder` fields
- Handles title renames — deletes the old file and creates a new one
- Deleted Apple Notes are left in Obsidian (one-way sync)
- Runs nightly via macOS launchd (no third-party dependencies)

## Example output

```markdown
---
created: 2026-07-10
modified: 2026-07-15
source: Apple Notes
folder: Personal
---

# My Note Title

Note content here...
```

## Requirements

- macOS (tested on macOS 15 Sequoia)
- Python 3.9+ (ships with macOS)
- Obsidian vault on local disk

## Setup

### 1. Clone or download

```bash
git clone https://github.com/yourusername/LavaFlow.git
cd LavaFlow
```

### 2. Edit the vault path

Open `lavaflow.py` and update `VAULT_DIR` to point to your Obsidian vault:

```python
VAULT_DIR = Path.home() / "Documents" / "YourVault" / "Apple Notes"
```

### 3. Run manually to do the initial sync

```bash
python3 lavaflow.py
```

macOS will prompt you to grant Automation permission for Python to control Notes.app — click **OK**.

### 4. Schedule nightly runs

Copy the plist to your LaunchAgents folder and load it:

```bash
cp com.kylepratt.lavaflow.plist ~/Library/LaunchAgents/
```

Open the plist and update the script path if needed, then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.kylepratt.lavaflow.plist
```

The sync will now run automatically every night at 11:59 PM.

## Usage

**Run a sync manually:**
```bash
python3 ~/LavaFlow/lavaflow.py
```

**Check the schedule is active:**
```bash
launchctl list | grep lavaflow
```

**Pause the nightly schedule:**
```bash
launchctl unload ~/Library/LaunchAgents/com.kylepratt.lavaflow.plist
```

**Resume the nightly schedule:**
```bash
launchctl load ~/Library/LaunchAgents/com.kylepratt.lavaflow.plist
```

**View logs:**
```bash
tail -50 ~/Library/Logs/lavaflow.log
```

## File structure

```
LavaFlow/
├── lavaflow.py                       # Main sync script
├── com.kylepratt.lavaflow.plist      # launchd schedule (11:59 PM nightly)
└── README.md
~/.lavaflow_state.json                # Tracks last-synced modification dates
~/Library/Logs/lavaflow.log          # Run logs
```

## Permissions

On first run, macOS may show an Automation permission prompt. If the nightly launchd job fails silently, go to:

**System Settings → Privacy & Security → Automation**

Make sure **Terminal** (or **Python**) has permission to control **Notes**.

## Limitations

- Apple Notes exports as **plain text** — rich text formatting (bold, tables, checklists) is not preserved
- Images and attachments in notes are not synced
- Notes inside locked/encrypted Apple Notes folders are skipped
