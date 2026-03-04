#!/usr/bin/env python3
"""State persistence for rate limit auto-detection and config."""

import json
import os
from pathlib import Path
from datetime import datetime, timezone

CONFIG_DIR = Path.home() / ".config" / "claude-usage"
STATE_FILE = CONFIG_DIR / "state.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_STATE = {
    "learned_cap": None,
    "cap_observations": [],
    "last_rate_limit_hit": None,
}

DEFAULT_CONFIG = {
    "manual_cap_override": None,
    "warning_threshold": 0.8,
    "critical_threshold": 0.95,
}


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    ensure_config_dir()
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return {**DEFAULT_STATE, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_STATE)


def save_state(state):
    ensure_config_dir()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def load_config():
    ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            pass
    # Write default config if it doesn't exist
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(config):
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_effective_cap(state, config):
    """Get the rate limit cap to use.

    Priority: manual override > learned cap > None.
    """
    if config.get("manual_cap_override"):
        return config["manual_cap_override"]
    if state.get("learned_cap"):
        return state["learned_cap"]
    return None


def update_cap_from_events(events, state, window_cost_at_time):
    """Update learned cap based on threshold events.

    Args:
        events: All parsed telemetry events.
        state: Current state dict.
        window_cost_at_time: Function(timestamp) -> rolling 5h cost at that time.

    Returns:
        Updated state dict.
    """
    threshold_events = [e for e in events if e["event_name"] == "tengu_cost_threshold_reached"]

    if not threshold_events:
        return state

    observations = state.get("cap_observations", [])

    for event in threshold_events:
        ts = event["timestamp"]
        ts_str = ts.isoformat()

        # Skip already-recorded observations
        if any(o.get("timestamp") == ts_str for o in observations):
            continue

        cost_at_hit = window_cost_at_time(ts)
        observations.append({
            "timestamp": ts_str,
            "cost_at_hit": cost_at_hit,
        })

    # Learned cap = max observed cost at threshold hit
    if observations:
        max_observed = max(o["cost_at_hit"] for o in observations)
        state["learned_cap"] = max_observed
        # Keep only last 20 observations
        state["cap_observations"] = observations[-20:]
        state["last_rate_limit_hit"] = observations[-1]["timestamp"]

    return state


def compute_window_cost_at_time(api_events):
    """Return a function that computes the rolling 5h cost at any given timestamp.

    Args:
        api_events: List of tengu_api_success events, sorted by timestamp.

    Returns:
        Callable(datetime) -> float
    """
    from datetime import timedelta

    def cost_at(ts):
        window_start = ts - timedelta(hours=5)
        return sum(
            e.get("cost_usd", 0)
            for e in api_events
            if window_start <= e["timestamp"] <= ts
        )

    return cost_at
