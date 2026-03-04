#!/usr/bin/env python3
"""Claude Code usage stats — SwiftBar plugin.

Displays 5-hour rolling window usage, current session stats,
daily/weekly totals, and per-project breakdown.

Data sources:
  ~/.claude/telemetry/*.json   (API call costs, tokens, durations)
  ~/.claude/projects/**/*.jsonl (session/project mapping)

State persisted at:
  ~/.config/claude-usage/state.json
  ~/.config/claude-usage/config.json
"""

import sys
import os

# Ensure imports work regardless of SwiftBar's working directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Follow symlink to find the real script directory
REAL_DIR = os.path.dirname(os.path.realpath(__file__))
if REAL_DIR not in sys.path:
    sys.path.insert(0, REAL_DIR)


def main():
    try:
        from parsers import parse_telemetry_events, get_current_session_id, get_session_project_map
        from metrics import compute_metrics
        from state import (
            load_state, save_state, load_config,
            update_cap_from_events, compute_window_cost_at_time,
        )
        from renderer import render

        # Parse telemetry (7 days of data)
        events = parse_telemetry_events(since_hours=168)

        # Detect current session and project mapping
        session_id = get_current_session_id()
        project_map = get_session_project_map()

        # Compute metrics
        metrics = compute_metrics(events, session_id, project_map)

        # Load and update state
        state = load_state()
        config = load_config()

        # Auto-detect rate limit cap from threshold events
        api_events = [e for e in events if e["event_name"] == "tengu_api_success"]
        cost_fn = compute_window_cost_at_time(api_events)
        state = update_cap_from_events(events, state, cost_fn)
        save_state(state)

        # Render output
        render(metrics, state, config)

    except Exception as e:
        # If anything fails, show error in menu bar
        print(f"CC: err | color=red")
        print("---")
        print(f"Error: {e} | color=red font=Menlo size=11")
        import traceback
        for line in traceback.format_exc().strip().split("\n"):
            print(f"{line} | font=Menlo size=10 color=gray")


if __name__ == "__main__":
    main()
