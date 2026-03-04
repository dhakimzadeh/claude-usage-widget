#!/usr/bin/env python3
"""Fetch usage data from Claude's OAuth API."""

import json
import subprocess
from datetime import datetime, timezone


def get_oauth_token():
    """Read the OAuth access token from macOS Keychain.

    Claude Code stores credentials in the Keychain under
    'Claude Code-credentials'.
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password",
             "-s", "Claude Code-credentials",
             "-a", subprocess.check_output(["whoami"]).decode().strip(),
             "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout.strip())
        return data.get("claudeAiOauth", {}).get("accessToken")
    except (json.JSONDecodeError, subprocess.SubprocessError, OSError):
        return None


def fetch_usage():
    """Fetch usage stats from Claude's OAuth API.

    Returns:
        Dict with keys: five_hour, seven_day, seven_day_sonnet, extra_usage.
        Each window has: utilization (0-100 float), resets_at (ISO timestamp).
        Returns None if the API call fails.
    """
    token = get_oauth_token()
    if not token:
        return None

    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "5",
             "https://api.anthropic.com/api/oauth/usage",
             "-H", f"Authorization: Bearer {token}",
             "-H", "anthropic-beta: oauth-2025-04-20",
             "-H", "Content-Type: application/json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        # Validate we got expected structure
        if "five_hour" not in data:
            return None

        return data

    except (json.JSONDecodeError, subprocess.SubprocessError, OSError):
        return None


def parse_reset_time(resets_at_str):
    """Parse resets_at timestamp and return seconds until reset.

    Returns 0 if already past or unparseable.
    """
    if not resets_at_str:
        return 0
    try:
        resets_at = datetime.fromisoformat(resets_at_str)
        now = datetime.now(timezone.utc)
        delta = (resets_at - now).total_seconds()
        return max(0, delta)
    except (ValueError, TypeError):
        return 0


if __name__ == "__main__":
    from metrics import format_duration

    usage = fetch_usage()
    if usage is None:
        print("Failed to fetch usage data")
    else:
        fh = usage.get("five_hour") or {}
        sd = usage.get("seven_day") or {}
        ss = usage.get("seven_day_sonnet") or {}

        print("=== From Claude API ===")
        print(f"  5-Hour:  {fh.get('utilization', '?')}%  resets in {format_duration(parse_reset_time(fh.get('resets_at')))}")
        print(f"  7-Day:   {sd.get('utilization', '?')}%  resets in {format_duration(parse_reset_time(sd.get('resets_at')))}")
        if ss:
            print(f"  Sonnet:  {ss.get('utilization', '?')}%  resets in {format_duration(parse_reset_time(ss.get('resets_at')))}")
