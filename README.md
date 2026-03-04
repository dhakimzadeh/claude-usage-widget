# Claude Code Usage Widget

A macOS menu bar widget that shows your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) usage stats at a glance. Built with [SwiftBar](https://github.com/swiftbar/SwiftBar) and Python.

No login required. No API keys. No network access. Everything is read from local telemetry files that Claude Code already writes to your machine.

## What You Get

A persistent menu bar item showing your 5-hour rolling usage window:

```
CC: 59% | 3h 27m
```

Click it to see the full dashboard:

```
5-Hour Window
[███████████░░░░░░░░░] 59%
$32.59 / $55.00 (learned cap)
Resets in: 3h 27m
API calls: 709

Current Session
Cost:       $18.17
Duration:   1h 10m
Burn rate:  $15.40/hr
In tokens:  444.8k
Out tokens: 68.0k
Cached:     26.5M
Model:      claude-opus-4-6
API calls:  314

Today
Total cost:  $32.59
Sessions:    4
API calls:   709

7-Day Rolling
Total cost:  $62.03
Avg/day:     $31.01
API calls:   1216

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

Claude Code writes telemetry data to `~/.claude/` as you use it. This widget reads those local files, computes usage metrics, and displays them via SwiftBar. There is:

- **No authentication** -- it reads files already on your disk
- **No API calls** -- everything is computed locally
- **No network access** -- the script never touches the internet
- **No Claude Code modification** -- it's a read-only observer

### Data Sources

| File | What It Contains |
|------|-----------------|
| `~/.claude/telemetry/*.json` | Per-request cost, tokens, model, duration |
| `~/.claude/projects/**/*.jsonl` | Session-to-project mapping |
| `~/.claude/history.jsonl` | Current active session ID |

### Architecture

```
claude-usage.5m.py    # SwiftBar entry point (runs every 5 min)
  -> parsers.py       # Reads telemetry + session files
  -> metrics.py       # Computes all dashboard numbers
  -> state.py         # Persists learned rate cap + config
  -> renderer.py      # Formats SwiftBar output
```

## Install

### Prerequisites

- macOS
- Python 3 (included with macOS)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and used at least once (so telemetry files exist)

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

5. **Verify** -- you should see `CC: XX%` (or `CC: $X.XX` if no cap is set yet) in your menu bar.

## Configuration

Config lives at `~/.config/claude-usage/config.json`. Created automatically on first run.

```json
{
  "manual_cap_override": 55.0,
  "warning_threshold": 0.8,
  "critical_threshold": 0.95
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `manual_cap_override` | Your 5-hour spending cap in USD. Set this to match your plan's limit. | `null` (auto-detect) |
| `warning_threshold` | Fraction of cap at which title turns orange | `0.8` |
| `critical_threshold` | Fraction of cap at which title turns red | `0.95` |

### Finding Your Cap

Check your usage on the [Claude settings page](https://console.anthropic.com/settings/usage). If it shows 57% used and the widget shows $31.50 in the 5-hour window, your cap is roughly `$31.50 / 0.57 = $55`.

### Rate Limit Auto-Detection

The widget also tries to learn your cap automatically by watching for `tengu_cost_threshold_reached` telemetry events. These fire when Claude Code hits an internal spending threshold. The learned cap is stored in `~/.config/claude-usage/state.json`.

The manual override in `config.json` always takes priority over the auto-detected value.

## Refresh Interval

The `5m` in the filename (`claude-usage.5m.py`) tells SwiftBar to re-run the script every 5 minutes. To change the interval, rename the symlink:

```bash
# Every 1 minute
mv ~/SwiftBarPlugins/claude-usage.5m.py ~/SwiftBarPlugins/claude-usage.1m.py

# Every 30 seconds
mv ~/SwiftBarPlugins/claude-usage.5m.py ~/SwiftBarPlugins/claude-usage.30s.py
```

You can also click **Refresh** in the dropdown to update immediately.

## Troubleshooting

**Widget shows "CC: --" in gray**
No telemetry data found. Make sure you've used Claude Code at least once. Check that `~/.claude/telemetry/` exists and has `.json` files.

**Widget shows "CC: err" in red**
Click it to see the error traceback. Common causes: Python version issues, missing telemetry directory, or file permission problems.

**Percentage doesn't match Claude settings page**
Adjust `manual_cap_override` in `~/.config/claude-usage/config.json`. See "Finding Your Cap" above.

**SwiftBar can't find the plugins folder**
`~/Library` is hidden by default in macOS file pickers. Use `~/SwiftBarPlugins` (or any visible directory) instead.

## License

MIT
