# Claude Code Usage — SwiftBar Widget

macOS menu bar widget showing Claude Code usage stats.

## Install

1. `brew install swiftbar`
2. Clone this repo to `~/Projects/claude-usage-widget`
3. Symlink the plugin:
   ```bash
   ln -sf ~/Projects/claude-usage-widget/claude-usage.5m.py \
     "$HOME/Library/Application Support/SwiftBar/Plugins/claude-usage.5m.py"
   ```
4. Open SwiftBar, set plugin directory to
   `~/Library/Application Support/SwiftBar/Plugins`

## What It Shows

- **5-hour rolling window** — cost, progress bar, reset timer
- **Current session** — cost, duration, burn rate, tokens, model
- **Today** — total cost, session count
- **7-day rolling** — total cost, daily average
- **Per-project breakdown** — cost by project (today)

## Rate Limit Detection

The widget auto-learns your rate limit cap by watching for
`tengu_cost_threshold_reached` telemetry events. Until a cap
is learned, it shows raw cost. You can also set a manual cap
in `~/.config/claude-usage/config.json`:

```json
{
  "manual_cap_override": 50.0,
  "warning_threshold": 0.8,
  "critical_threshold": 0.95
}
```

## Data Sources

All data is read locally — no API calls, no network access.

- `~/.claude/telemetry/*.json` — per-request cost and tokens
- `~/.claude/projects/**/*.jsonl` — session/project mapping
- `~/.claude/history.jsonl` — current session detection
