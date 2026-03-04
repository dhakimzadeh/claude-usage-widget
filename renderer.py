#!/usr/bin/env python3
"""SwiftBar output renderer for Claude Code usage widget."""

import os
from metrics import format_duration, format_tokens
from api import parse_reset_time

# 16pt @ 2x retina (32x32px) Claude sparkle icon — matches system menu bar icon specs
# templateImage: macOS auto-adapts to light/dark mode
ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABs0lEQVR4nGNgGAWjgHiwD4gn4JCTorXl04H4PxTrYpEHiX+hpQPykRxwAofcB1o6gAHJAf/RxKdCxVbiUE824EXjqyMZuhdJ/ABULAGHY13IdQDMgDAksfNI4txQsWdo/PcMuEOLLAeA8HqoGAuS2Ek0dSDQhqaPixIHsKEZBsKcQHwazVIYWwtNbRElliODJjSDW5HYW7E4EoQPUMtyGGDHYREujA5ACdqdGg7pIMLytUBcBcSHsMhVE2PJfiA+DsSbgHgeEPcBcQ4QxwOxLRBHE+EIZPwciGcCsTOxvqxgwMxKpOCLQJxFrGXkAA0SHXSfAVJ811PD8iVEWGgIxJOB+B8WuVZyLS5FMgRU8lXgccA3NL2gEKuBOopkgB7cwUAsCWW/A+JtUPZ3LA5hIcdCZOCCZNg+JHHkvP4YiF8AsQSSuD6aGrKBCRDvBmIzJLEdUINVkRyzC8peCeW/RXIciM9OqUNgoAFqYCmSGIhfh8YH4Xo0PRQDTahB15HEdKFisUhinAxUCn50cI4BEqTIANYUU0ETnwgVF6O2I9ABrCakWhyTCkC55C1BVaNgFBAAAEbh5LvsZw07AAAAAElFTkSuQmCC"


def progress_bar(pct, width=20):
    """Render a text progress bar. pct is 0-100."""
    fraction = max(0, min(pct / 100, 1.0))
    filled = int(fraction * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def title_color(pct, config):
    """Determine title color based on usage percentage (0-100)."""
    if pct is None:
        return ""
    warning = config.get("warning_threshold", 0.8) * 100
    critical = config.get("critical_threshold", 0.95) * 100
    if pct >= critical:
        return " | color=red"
    if pct >= warning:
        return " | color=orange"
    return ""


def render(api_usage, session_metrics, config):
    """Render SwiftBar output to stdout.

    Args:
        api_usage: Dict from fetch_usage() (Claude API data), or None.
        session_metrics: Dict with current_session and projects from local telemetry.
        config: Dict from load_config().
    """
    lines = []

    # --- Extract API data ---
    if api_usage:
        fh = api_usage.get("five_hour") or {}
        sd = api_usage.get("seven_day") or {}
        ss = api_usage.get("seven_day_sonnet") or {}

        fh_pct = fh.get("utilization")
        fh_reset = parse_reset_time(fh.get("resets_at"))
        sd_pct = sd.get("utilization")
        sd_reset = parse_reset_time(sd.get("resets_at"))
        ss_pct = ss.get("utilization") if ss else None
    else:
        fh_pct = None
        fh_reset = 0
        sd_pct = None
        sd_reset = 0
        ss_pct = None

    # --- Menu bar title ---
    if fh_pct is not None:
        reset_str = format_duration(fh_reset)
        color = title_color(fh_pct, config)
        lines.append(f"{fh_pct:.0f}% | templateImage={ICON_B64}{color}")
    else:
        lines.append(f"? | templateImage={ICON_B64} color=red")

    lines.append("---")

    # --- 5-Hour Window (from API) ---
    lines.append("5-Hour Window | disabled=true size=14")
    if fh_pct is not None:
        bar = progress_bar(fh_pct)
        lines.append(f"{bar} {fh_pct:.0f}% | font=Menlo size=12")
        lines.append(f"Resets in: {format_duration(fh_reset)} | font=Menlo size=12")
    else:
        lines.append("Could not fetch usage data | font=Menlo size=12 color=red")
        lines.append("Check OAuth token in Keychain | font=Menlo size=11 color=gray")

    lines.append("---")

    # --- 7-Day Window (from API) ---
    lines.append("7-Day Window | disabled=true size=14")
    if sd_pct is not None:
        bar = progress_bar(sd_pct)
        lines.append(f"{bar} {sd_pct:.0f}% | font=Menlo size=12")
        lines.append(f"Resets in: {format_duration(sd_reset)} | font=Menlo size=12")
    else:
        lines.append("-- | font=Menlo size=12 color=gray")

    if ss_pct is not None:
        lines.append(f"Sonnet: {ss_pct:.0f}% | font=Menlo size=12 color=gray")

    lines.append("---")

    # --- Current Session (from local telemetry) ---
    s = session_metrics.get("current_session", {})
    if s.get("api_calls", 0) > 0:
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

    # --- Projects (today, from local telemetry) ---
    projects = session_metrics.get("projects", {})
    if projects:
        lines.append("Projects (today) | disabled=true size=14")
        for name, cost in projects.items():
            lines.append(f"{name:<20s} ${cost:.2f} | font=Menlo size=12")
        lines.append("---")

    # --- Actions ---
    lines.append("⟳ Refresh | refresh=true")
    config_path = os.path.expanduser("~/.config/claude-usage/config.json")
    lines.append(f"⚙ Config... | bash=open param1={config_path} terminal=false")

    lines.append("---")

    # --- About ---
    lines.append("About Claude Usage Widget | disabled=true size=14")
    lines.append("v2.0.0 | font=Menlo size=11 color=gray")
    lines.append("Usage % from Claude API (OAuth) | font=Menlo size=11 color=gray")
    lines.append("Session stats from local telemetry | font=Menlo size=11 color=gray")
    lines.append("GitHub | href=https://github.com/dhakimzadeh/claude-usage-widget")

    for line in lines:
        print(line)
