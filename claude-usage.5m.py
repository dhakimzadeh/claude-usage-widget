#!/usr/bin/env python3

# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>

"""Claude Code usage stats — SwiftBar plugin.

Usage percentages and reset timers come from Claude's OAuth API
(same source as the /usage command in Claude Code).

Session-level stats (cost, tokens, burn rate) and per-project
breakdowns come from local telemetry files.

Data sources:
  Claude API:  https://api.anthropic.com/api/oauth/usage
  Local:       ~/.claude/telemetry/*.json, ~/.claude/projects/**/*.jsonl

Config:  ~/.config/claude-usage/config.json
"""

import sys
import os

# Follow symlink to find the real script directory
REAL_DIR = os.path.dirname(os.path.realpath(__file__))
if REAL_DIR not in sys.path:
    sys.path.insert(0, REAL_DIR)


def main():
    try:
        from api import fetch_usage
        from parsers import parse_telemetry_events, get_current_session_id, get_session_project_map
        from metrics import compute_metrics
        from state import load_config
        from renderer import render

        # Fetch official usage from Claude API
        api_usage = fetch_usage()

        # Parse local telemetry for session/project detail
        events = parse_telemetry_events(since_hours=168)
        session_id = get_current_session_id()
        project_map = get_session_project_map()
        metrics = compute_metrics(events, session_id, project_map)

        config = load_config()

        # Session-level metrics to pass to renderer
        session_metrics = {
            "current_session": metrics["current_session"],
            "projects": metrics["projects"],
        }

        render(api_usage, session_metrics, config)

    except Exception as e:
        print("err | color=red")
        print("---")
        print(f"Error: {e} | color=red font=Menlo size=11")
        import traceback
        for line in traceback.format_exc().strip().split("\n"):
            print(f"{line} | font=Menlo size=10 color=gray")


if __name__ == "__main__":
    main()
