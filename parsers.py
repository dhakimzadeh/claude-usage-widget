#!/usr/bin/env python3
"""Parsers for Claude Code local data files."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

TELEMETRY_DIR = Path.home() / ".claude" / "telemetry"
PROJECTS_DIR = Path.home() / ".claude" / "projects"
HISTORY_FILE = Path.home() / ".claude" / "history.jsonl"


def parse_telemetry_events(since_hours=168):
    """Parse telemetry files for API success events within the time window.

    Args:
        since_hours: How far back to look (default 168 = 7 days).

    Returns:
        List of dicts with keys: timestamp, session_id, cost_usd, model,
        input_tokens, output_tokens, cached_input_tokens, uncached_input_tokens,
        duration_ms, stop_reason, query_source, fast_mode, event_name.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - (since_hours * 3600)
    events = []

    if not TELEMETRY_DIR.exists():
        return events

    for fpath in TELEMETRY_DIR.glob("*.json"):
        # Skip small/empty files
        if fpath.stat().st_size < 10:
            continue
        # Skip files older than our window (use mtime as rough filter)
        if fpath.stat().st_mtime < cutoff:
            continue

        try:
            with open(fpath, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    event_data = record.get("event_data", {})
                    event_name = event_data.get("event_name", "")

                    if event_name not in ("tengu_api_success", "tengu_exit", "tengu_cost_threshold_reached"):
                        continue

                    ts_str = event_data.get("client_timestamp", "")
                    if not ts_str:
                        continue

                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except ValueError:
                        continue

                    if ts.timestamp() < cutoff:
                        continue

                    # Parse additional_metadata (JSON-encoded string)
                    meta_str = event_data.get("additional_metadata", "{}")
                    try:
                        meta = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
                    except json.JSONDecodeError:
                        meta = {}

                    event = {
                        "timestamp": ts,
                        "session_id": event_data.get("session_id", ""),
                        "event_name": event_name,
                        "model": event_data.get("model", ""),
                    }

                    if event_name == "tengu_api_success":
                        event.update({
                            "cost_usd": meta.get("costUSD", 0.0),
                            "input_tokens": meta.get("inputTokens", 0),
                            "output_tokens": meta.get("outputTokens", 0),
                            "cached_input_tokens": meta.get("cachedInputTokens", 0),
                            "uncached_input_tokens": meta.get("uncachedInputTokens", 0),
                            "duration_ms": meta.get("durationMs", 0),
                            "stop_reason": meta.get("stop_reason", ""),
                            "query_source": meta.get("querySource", ""),
                            "fast_mode": meta.get("fastMode", False),
                        })
                    elif event_name == "tengu_exit":
                        event.update({
                            "last_session_cost": meta.get("last_session_cost", 0.0),
                            "last_session_duration": meta.get("last_session_duration", 0),
                            "last_session_input_tokens": meta.get("last_session_total_input_tokens", 0),
                            "last_session_output_tokens": meta.get("last_session_total_output_tokens", 0),
                            "last_session_cache_creation": meta.get("last_session_total_cache_creation_input_tokens", 0),
                            "last_session_cache_read": meta.get("last_session_total_cache_read_input_tokens", 0),
                            "last_session_id": meta.get("last_session_id", ""),
                        })

                    events.append(event)

        except (OSError, PermissionError):
            continue

    events.sort(key=lambda e: e["timestamp"])
    return events


def get_current_session_id():
    """Get the most recent active session ID.

    Reads the last entry from ~/.claude/history.jsonl.
    Falls back to the most recently modified session .jsonl file.
    """
    # Try history.jsonl first (most reliable)
    if HISTORY_FILE.exists():
        last_line = None
        try:
            with open(HISTORY_FILE, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        last_line = stripped
            if last_line:
                record = json.loads(last_line)
                session_id = record.get("sessionId", "")
                if session_id:
                    return session_id
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: most recently modified .jsonl in projects dir
    if not PROJECTS_DIR.exists():
        return None

    newest = None
    newest_mtime = 0
    for fpath in PROJECTS_DIR.rglob("*.jsonl"):
        # Skip subagent files
        if "subagents" in str(fpath):
            continue
        mtime = fpath.stat().st_mtime
        if mtime > newest_mtime:
            newest_mtime = mtime
            newest = fpath

    if newest:
        return newest.stem

    return None


def get_session_project_map():
    """Map session IDs to project paths.

    Returns dict: session_id -> project_path (e.g., "/Users/dan/Projects/RekordShelf")
    """
    session_map = {}

    if not PROJECTS_DIR.exists():
        return session_map

    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # Decode the project path from dir name (dashes replace slashes)
        # e.g., "-Users-dan-Projects-RekordShelf" -> "/Users/dan/Projects/RekordShelf"
        project_path = project_dir.name.replace("-", "/")
        # Use the last path component as a friendly name
        friendly_name = project_path.rstrip("/").split("/")[-1] if "/" in project_path else project_path

        for fpath in project_dir.glob("*.jsonl"):
            if "subagents" in str(fpath):
                continue
            session_id = fpath.stem
            session_map[session_id] = friendly_name

    return session_map


if __name__ == "__main__":
    events = parse_telemetry_events(since_hours=24)
    api_events = [e for e in events if e["event_name"] == "tengu_api_success"]
    print(f"Last 24h: {len(api_events)} API calls")
    total_cost = sum(e.get("cost_usd", 0) for e in api_events)
    print(f"Total cost: ${total_cost:.2f}")

    current = get_current_session_id()
    print(f"Current session: {current}")

    project_map = get_session_project_map()
    print(f"Known projects: {len(project_map)} sessions across projects")
    # Show unique project names
    unique_projects = set(project_map.values())
    for p in sorted(unique_projects):
        print(f"  - {p}")
