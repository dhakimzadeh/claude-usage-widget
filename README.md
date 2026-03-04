# Claude Code Usage Widget

A macOS menu bar widget that shows your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) usage stats at a glance. Built with [SwiftBar](https://github.com/swiftbar/SwiftBar) and Python.

Usage percentages and reset timers come directly from Claude's API -- the same source as the `/usage` command in Claude Code. Session-level detail (cost, tokens, burn rate) and per-project breakdowns come from local telemetry.

## What You Get

A persistent menu bar item showing your 5-hour rolling usage:

```
CC: 74% | 2h 39m
```

Click it to see the full dashboard:

```
5-Hour Window
[██████████████░░░░░░] 74%
Resets in: 2h 39m

7-Day Window
[██████████░░░░░░░░░░] 51%
Resets in: 46h 39m
Sonnet: 3%

Current Session
Cost:       $18.17
Duration:   1h 10m
Burn rate:  $15.40/hr
In tokens:  444.8k
Out tokens: 68.0k
Cached:     26.5M
Model:      claude-opus-4-6
API calls:  314

Projects (today)
RekordShelf          $25.75
dan                  $6.84
```

The menu bar text changes color as you approach your limit:

| Usage     | Color  |
|-----------|--------|
| < 80%     | Normal |
| 80 - 94%  | Orange |
| 95 - 100% | Red    |

## How It Works

### Authentication

**No manual login or API keys required.** The widget reads the OAuth token that Claude Code already stores in your macOS Keychain (under "Claude Code-credentials"). As long as you're logged into Claude Code, the widget works.

### Data Sources

| Source | What It Provides | How |
|--------|-----------------|-----|
| Claude OAuth API | 5-hour usage %, 7-day usage %, reset timers | Reads token from Keychain, calls `api.anthropic.com/api/oauth/usage` |
| Local telemetry | Session cost, tokens, burn rate, model | Reads `~/.claude/telemetry/*.json` |
| Local project files | Per-project cost breakdown | Reads `~/.claude/projects/**/*.jsonl` |

The usage percentages are the exact same numbers you see on Claude's settings page and in the `/usage` command. No local estimation or cap guessing.

### Architecture

```
claude-usage.5m.py    # SwiftBar entry point (runs every 5 min)
  -> api.py           # Fetches usage % from Claude OAuth API
  -> parsers.py       # Reads local telemetry + session files
  -> metrics.py       # Computes session/project stats
  -> state.py         # Config persistence
  -> renderer.py      # Formats SwiftBar output
```

## Install

### Prerequisites

- macOS
- Python 3 (included with macOS)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and logged in

### Steps

1. **Install SwiftBar**

   ```bash
   brew install swiftbar
   ```

2. **Clone this repo**

   ```bash
   git clone https://github.com/dhakimzadeh/claude-usage-widget.git ~/Projects/claude-usage-widget
   ```

3. **Create a plugins directory and symlink**

   ```bash
   mkdir -p ~/SwiftBarPlugins
   ln -sf ~/Projects/claude-usage-widget/claude-usage.5m.py ~/SwiftBarPlugins/claude-usage.5m.py
   ```

4. **Launch SwiftBar and set the plugin directory**

   Open SwiftBar. When prompted for a plugin directory, select `~/SwiftBarPlugins`.

5. **Verify** -- you should see `CC: XX%` in your menu bar within a few seconds.

## Configuration

Config lives at `~/.config/claude-usage/config.json`. Created automatically on first run.

```json
{
  "warning_threshold": 0.8,
  "critical_threshold": 0.95
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `warning_threshold` | Fraction (0-1) at which title turns orange | `0.8` |
| `critical_threshold` | Fraction (0-1) at which title turns red | `0.95` |

## Refresh Interval

The `5m` in the filename tells SwiftBar to re-run every 5 minutes. To change it, rename the symlink:

```bash
# Every 1 minute
mv ~/SwiftBarPlugins/claude-usage.5m.py ~/SwiftBarPlugins/claude-usage.1m.py

# Every 30 seconds
mv ~/SwiftBarPlugins/claude-usage.5m.py ~/SwiftBarPlugins/claude-usage.30s.py
```

You can also click **Refresh** in the dropdown to update immediately.

## Troubleshooting

**Widget shows "CC: ?" in red**
The OAuth API call failed. Make sure you're logged into Claude Code (`claude` in terminal). The widget reads the token from your macOS Keychain automatically.

**Widget shows "CC: err" in red**
Click it to see the error traceback in the dropdown.

**SwiftBar can't find the plugins folder**
`~/Library` is hidden in macOS file pickers. Use `~/SwiftBarPlugins` (or any visible directory) instead.

**Session stats show wrong session**
The widget picks up the most recent session from `~/.claude/history.jsonl`. If you have multiple Claude Code instances, it shows the latest one.

## License

MIT
