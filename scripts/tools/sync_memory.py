#!/usr/bin/env python3
"""
Hermes Memory Sync Script

This script synchronizes the long-term memory from /root/.hermes/memory/core/long-term.md
to /root/.hermes/SOUL.md, ensuring that the agent's identity and memory are always up-to-date.

Usage:
    python3 sync_memory.py [--watch] [--interval SECONDS]

Options:
    --watch      Run continuously, checking for changes every INTERVAL seconds
    --interval   How often to check for changes (default: 60 seconds)
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Paths
MEMORY_FILE = Path("/root/.hermes/memory/core/long-term.md")
SOUL_FILE = Path("/root/.hermes/SOUL.md")
BACKUP_DIR = Path("/root/.hermes/memory/backups")

def ensure_dirs():
    """Ensure all required directories exist."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def read_file(path: Path) -> str:
    """Read a file and return its content."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return ""

def write_file(path: Path, content: str) -> bool:
    """Write content to a file."""
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error writing {path}: {e}")
        return False

def backup_soul():
    """Create a backup of the current SOUL.md."""
    if SOUL_FILE.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"SOUL_{timestamp}.md"
        try:
            backup_path.write_text(SOUL_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Backed up SOUL.md to {backup_path}")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")

def sync_memory_to_soul():
    """Sync long-term memory to SOUL.md."""
    # Read the long-term memory
    memory_content = read_file(MEMORY_FILE)
    if not memory_content:
        print("Warning: Long-term memory file is empty or missing")
        return False
    
    # Read current SOUL.md
    soul_content = read_file(SOUL_FILE)
    
    # Create new SOUL.md content
    # We'll keep the first line (Hermes Agent Persona) and add the memory content
    lines = soul_content.split('\n')
    
    # Find the first line
    first_line = lines[0] if lines else "# Hermes Agent Persona"
    
    # Create new content with just the first line and memory content
    new_soul = f"{first_line}\n\n{memory_content}"
    
    # Backup current SOUL.md
    backup_soul()
    
    # Write updated SOUL.md
    if write_file(SOUL_FILE, new_soul):
        print(f"Synced memory to SOUL.md at {datetime.now()}")
        return True
    return False

def watch_mode(interval: int):
    """Run continuously, checking for changes every interval seconds."""
    print(f"Starting watch mode, checking every {interval} seconds...")
    print("Press Ctrl+C to stop")
    
    last_modified = 0
    try:
        while True:
            try:
                current_modified = MEMORY_FILE.stat().st_mtime
                if current_modified > last_modified:
                    print(f"Change detected in long-term memory, syncing...")
                    if sync_memory_to_soul():
                        last_modified = current_modified
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nStopping watch mode...")
                break
            except Exception as e:
                print(f"Error in watch loop: {e}")
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")

def main():
    parser = argparse.ArgumentParser(description="Sync Hermes long-term memory to SOUL.md")
    parser.add_argument("--watch", action="store_true", help="Run continuously, watching for changes")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds (default: 60)")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_dirs()
    
    if args.watch:
        watch_mode(args.interval)
    else:
        # One-time sync
        if sync_memory_to_soul():
            print("Memory sync completed successfully")
        else:
            print("Memory sync failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
