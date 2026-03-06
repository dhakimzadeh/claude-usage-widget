#!/usr/bin/env python3
"""Fetch usage data from Claude's OAuth API."""

import json
import subprocess
import time
from datetime import datetime, timezone


def get_oauth_credentials():
    """Read OAuth credentials from macOS Keychain.

    Claude Code stores credentials in the Keychain under
    'Claude Code-credentials'. Returns dict with accessToken,
    refreshToken, expiresAt, or None on failure.
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
        return data.get("claudeAiOauth")
    except (json.JSONDecodeError, subprocess.SubprocessError, OSError):
        return None


def is_token_expired(creds):
    """Check if the access token has expired.

    expiresAt is stored as Unix timestamp in milliseconds.
    Returns True if expired or expiring within 60 seconds.
    """
    expires_at = creds.get("expiresAt", 0)
    # Convert ms to seconds, add 60s buffer
    return time.time() > (expires_at / 1000) - 60


def fetch_usage():
    """Fetch usage stats from Claude's OAuth API.

    Returns:
        Dict with keys: five_hour, seven_day, seven_day_sonnet, extra_usage.
        Each window has: utilization (0-100 float), resets_at (ISO timestamp).
        Returns {"error": "reason"} on known failures, None on unknown.
    """
    creds = get_oauth_credentials()
    if not creds:
        return {"error": "no_credentials"}

    token = creds.get("accessToken")
    if not token:
        return {"error": "no_credentials"}

    if is_token_expired(creds):
        return {"error": "token_expired"}

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
            return {"error": "api_failed"}

        data = json.loads(result.stdout)

        if "error" in data:
            error_info = data.get("error", {})
            error_type = error_info.get("type", "") if isinstance(error_info, dict) else str(error_info)
            if "auth" in error_type.lower() or "token" in error_type.lower() or "permission" in error_type.lower():
                return {"error": "token_expired"}
            if "rate_limit" in error_type.lower():
                return {"error": "rate_limited"}
            return {"error": "api_failed"}

        if "five_hour" not in data:
            return {"error": "api_failed"}

        return data

    except (json.JSONDecodeError, subprocess.SubprocessError, OSError):
        return {"error": "api_failed"}


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
    if usage is None or "error" in usage:
        print(f"Failed to fetch usage data: {usage}")
    else:
        fh = usage.get("five_hour") or {}
        sd = usage.get("seven_day") or {}
        ss = usage.get("seven_day_sonnet") or {}

        print("=== From Claude API ===")
        print(f"  5-Hour:  {fh.get('utilization', '?')}%  resets in {format_duration(parse_reset_time(fh.get('resets_at')))}")
        print(f"  7-Day:   {sd.get('utilization', '?')}%  resets in {format_duration(parse_reset_time(sd.get('resets_at')))}")
        if ss:
            print(f"  Sonnet:  {ss.get('utilization', '?')}%  resets in {format_duration(parse_reset_time(ss.get('resets_at')))}")
