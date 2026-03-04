#!/usr/bin/env python3
"""Compute usage metrics from parsed telemetry events."""

from datetime import datetime, timezone, timedelta
from collections import defaultdict


def compute_metrics(events, current_session_id, session_project_map):
    """Compute all dashboard metrics.

    Args:
        events: List of parsed telemetry events (from parse_telemetry_events).
        current_session_id: Current active session ID string.
        session_project_map: Dict mapping session_id -> project_name.

    Returns:
        Dict with keys: window_5h, current_session, today, week, projects.
    """
    now = datetime.now(timezone.utc)
    five_hours_ago = now - timedelta(hours=5)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    api_events = [e for e in events if e["event_name"] == "tengu_api_success"]

    # --- 5-hour rolling window ---
    window_events = [e for e in api_events if e["timestamp"] >= five_hours_ago]
    window_cost = sum(e.get("cost_usd", 0) for e in window_events)

    # Reset time: when the oldest event in the window drops out
    if window_events:
        oldest_in_window = min(e["timestamp"] for e in window_events)
        reset_delta = (oldest_in_window + timedelta(hours=5)) - now
        reset_seconds = max(0, reset_delta.total_seconds())
    else:
        reset_seconds = 0

    window_5h = {
        "cost": window_cost,
        "event_count": len(window_events),
        "reset_seconds": reset_seconds,
    }

    # --- Current session ---
    session_events = [e for e in api_events if e.get("session_id") == current_session_id]
    session_cost = sum(e.get("cost_usd", 0) for e in session_events)
    session_input = sum(e.get("input_tokens", 0) for e in session_events)
    session_output = sum(e.get("output_tokens", 0) for e in session_events)
    session_cached = sum(e.get("cached_input_tokens", 0) for e in session_events)

    if session_events:
        session_start = min(e["timestamp"] for e in session_events)
        session_duration_s = (now - session_start).total_seconds()
        burn_rate = (session_cost / (session_duration_s / 3600)) if session_duration_s > 0 else 0
        model = session_events[-1].get("model", "unknown")
    else:
        session_duration_s = 0
        burn_rate = 0
        model = "unknown"

    current_session = {
        "cost": session_cost,
        "duration_seconds": session_duration_s,
        "burn_rate_per_hour": burn_rate,
        "input_tokens": session_input,
        "output_tokens": session_output,
        "cached_tokens": session_cached,
        "model": model,
        "api_calls": len(session_events),
    }

    # --- Today ---
    today_events = [e for e in api_events if e["timestamp"] >= today_start]
    today_cost = sum(e.get("cost_usd", 0) for e in today_events)
    today_sessions = len(set(e.get("session_id", "") for e in today_events))

    today = {
        "cost": today_cost,
        "sessions": today_sessions,
        "api_calls": len(today_events),
    }

    # --- 7-day rolling ---
    week_events = [e for e in api_events if e["timestamp"] >= week_ago]
    week_cost = sum(e.get("cost_usd", 0) for e in week_events)
    # Compute daily average based on actual days with usage
    days_with_usage = len(set(e["timestamp"].date() for e in week_events)) if week_events else 1

    week = {
        "cost": week_cost,
        "avg_per_day": week_cost / max(days_with_usage, 1),
        "api_calls": len(week_events),
    }

    # --- Per-project breakdown (today) ---
    project_costs = defaultdict(float)
    for e in today_events:
        sid = e.get("session_id", "")
        project = session_project_map.get(sid, "unknown")
        project_costs[project] += e.get("cost_usd", 0)

    # Sort by cost descending
    projects = dict(sorted(project_costs.items(), key=lambda x: -x[1]))

    return {
        "window_5h": window_5h,
        "current_session": current_session,
        "today": today,
        "week": week,
        "projects": projects,
    }


def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds <= 0:
        return "0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def format_tokens(count):
    """Format token count with k/M suffix."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}k"
    return str(count)


if __name__ == "__main__":
    from parsers import parse_telemetry_events, get_current_session_id, get_session_project_map

    events = parse_telemetry_events(since_hours=168)
    session_id = get_current_session_id()
    project_map = get_session_project_map()
    m = compute_metrics(events, session_id, project_map)

    print("=== 5-Hour Window ===")
    print(f"  Cost: ${m['window_5h']['cost']:.2f}")
    print(f"  Requests: {m['window_5h']['event_count']}")
    print(f"  Resets in: {format_duration(m['window_5h']['reset_seconds'])}")

    print("=== Current Session ===")
    print(f"  Cost: ${m['current_session']['cost']:.2f}")
    print(f"  Duration: {format_duration(m['current_session']['duration_seconds'])}")
    print(f"  Burn rate: ${m['current_session']['burn_rate_per_hour']:.2f}/hr")
    print(f"  In: {format_tokens(m['current_session']['input_tokens'])}")
    print(f"  Out: {format_tokens(m['current_session']['output_tokens'])}")
    print(f"  Cached: {format_tokens(m['current_session']['cached_tokens'])}")
    print(f"  Model: {m['current_session']['model']}")

    print("=== Today ===")
    print(f"  Cost: ${m['today']['cost']:.2f}")
    print(f"  Sessions: {m['today']['sessions']}")

    print("=== 7-Day ===")
    print(f"  Cost: ${m['week']['cost']:.2f}")
    print(f"  Avg/day: ${m['week']['avg_per_day']:.2f}")

    print("=== Projects (today) ===")
    for name, cost in m["projects"].items():
        print(f"  {name}: ${cost:.2f}")
