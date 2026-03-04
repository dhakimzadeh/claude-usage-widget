#!/usr/bin/env python3
"""SwiftBar output renderer for Claude Code usage widget."""

import os
from metrics import format_duration, format_tokens


def progress_bar(fraction, width=20):
    """Render a text progress bar using block characters."""
    filled = int(fraction * width)
    filled = max(0, min(filled, width))
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def title_color(fraction, config):
    """Determine title color based on usage fraction."""
    if fraction is None:
        return ""
    if fraction >= config.get("critical_threshold", 0.95):
        return " | color=red"
    if fraction >= config.get("warning_threshold", 0.8):
        return " | color=orange"
    return ""


def render(metrics, state, config):
    """Render SwiftBar output to stdout.

    Args:
        metrics: Dict from compute_metrics().
        state: Dict from load_state().
        config: Dict from load_config().
    """
    from state import get_effective_cap
    lines = []

    cap = get_effective_cap(state, config)
    w = metrics["window_5h"]
    s = metrics["current_session"]

    # Handle no data
    if not any([w["cost"], s["cost"], metrics["today"]["cost"]]):
        lines.append("CC: -- | color=gray")
        lines.append("---")
        lines.append("No Claude Code usage data found | disabled=true")
        lines.append("---")
        lines.append("⟳ Refresh | refresh=true")
        for line in lines:
            print(line)
        return

    # --- Menu bar title ---
    if cap and cap > 0:
        fraction = w["cost"] / cap
        pct = min(fraction * 100, 100)
        reset_str = format_duration(w["reset_seconds"])
        color = title_color(fraction, config)
        lines.append(f"CC: {pct:.0f}% | {reset_str}{color}")
    else:
        lines.append(f"CC: ${w['cost']:.2f}")

    lines.append("---")

    # --- 5-Hour Window ---
    lines.append("5-Hour Window | disabled=true size=14")
    if cap and cap > 0:
        fraction = w["cost"] / cap
        bar = progress_bar(fraction)
        pct = min(fraction * 100, 100)
        lines.append(f"{bar} {pct:.0f}% | font=Menlo size=12")
        lines.append(f"${w['cost']:.2f} / ${cap:.2f} (learned cap) | font=Menlo size=12")
    else:
        lines.append(f"${w['cost']:.2f} (no cap learned yet) | font=Menlo size=12")
    if w["reset_seconds"] > 0:
        lines.append(f"Resets in: {format_duration(w['reset_seconds'])} | font=Menlo size=12")
    lines.append(f"API calls: {w['event_count']} | font=Menlo size=12 color=gray")

    lines.append("---")

    # --- Current Session ---
    lines.append("Current Session | disabled=true size=14")
    lines.append(f"Cost:       ${s['cost']:.2f} | font=Menlo size=12")
    lines.append(f"Duration:   {format_duration(s['duration_seconds'])} | font=Menlo size=12")
    lines.append(f"Burn rate:  ${s['burn_rate_per_hour']:.2f}/hr | font=Menlo size=12")
    lines.append(f"In tokens:  {format_tokens(s['input_tokens'])} | font=Menlo size=12")
    lines.append(f"Out tokens: {format_tokens(s['output_tokens'])} | font=Menlo size=12")
    lines.append(f"Cached:     {format_tokens(s['cached_tokens'])} | font=Menlo size=12")
    lines.append(f"Model:      {s['model']} | font=Menlo size=12")
    lines.append(f"API calls:  {s['api_calls']} | font=Menlo size=12 color=gray")

    lines.append("---")

    # --- Today ---
    t = metrics["today"]
    lines.append("Today | disabled=true size=14")
    lines.append(f"Total cost:  ${t['cost']:.2f} | font=Menlo size=12")
    lines.append(f"Sessions:    {t['sessions']} | font=Menlo size=12")
    lines.append(f"API calls:   {t['api_calls']} | font=Menlo size=12 color=gray")

    lines.append("---")

    # --- 7-Day Rolling ---
    wk = metrics["week"]
    lines.append("7-Day Rolling | disabled=true size=14")
    lines.append(f"Total cost:  ${wk['cost']:.2f} | font=Menlo size=12")
    lines.append(f"Avg/day:     ${wk['avg_per_day']:.2f} | font=Menlo size=12")
    lines.append(f"API calls:   {wk['api_calls']} | font=Menlo size=12 color=gray")

    lines.append("---")

    # --- Projects (today) ---
    projects = metrics["projects"]
    if projects:
        lines.append("Projects (today) | disabled=true size=14")
        for name, cost in projects.items():
            lines.append(f"{name:<20s} ${cost:.2f} | font=Menlo size=12")
    else:
        lines.append("No project data today | disabled=true color=gray")

    lines.append("---")

    # --- Actions ---
    # Refresh triggers SwiftBar to re-run the plugin
    lines.append("⟳ Refresh | refresh=true")
    config_path = os.path.expanduser("~/.config/claude-usage/config.json")
    lines.append(f"⚙ Config... | bash=open param1={config_path} terminal=false")

    lines.append("---")

    # --- About ---
    lines.append("About Claude Usage Widget | disabled=true size=14")
    lines.append("v1.0.0 | font=Menlo size=11 color=gray")
    lines.append("Reads local Claude Code telemetry — no login, | font=Menlo size=11 color=gray")
    lines.append("no API keys, no network access required. | font=Menlo size=11 color=gray")
    lines.append("Data: ~/.claude/telemetry/ | font=Menlo size=11 color=gray")
    lines.append("Config: ~/.config/claude-usage/ | font=Menlo size=11 color=gray")
    lines.append("GitHub | href=https://github.com/dhakimzadeh/claude-usage-widget")

    # Print all lines
    for line in lines:
        print(line)
