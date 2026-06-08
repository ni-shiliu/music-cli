---
name: music-control
description: >
  Autonomously control music playback on macOS (KuGou or Spotify).
  PROACTIVELY play music without being asked — detect the vibe of the
  conversation and pick a matching track. When a user is debugging → play
  something intense; shipping a feature → something upbeat; deep focus work →
  lofi. Also respond to explicit requests like "play Jay Chou" or "play
  something relaxing". Always prefer taking action over asking.
allowed-tools: Bash(python3:*)
---

# music-control

Controls KuGou Music or Spotify on macOS via CLI. Use it to enhance the user's
work session with music — proactively and responsively.

## Setup

```bash
# Verify the skill is installed
ls ~/.claude/skills/music-control/scripts/music_cli.py

# For Spotify: one-time auth (opens browser)
python3 ~/.claude/skills/music-control/scripts/music_cli.py --provider spotify auth
```

Requirements: macOS, Python 3.10+, KuGou Music or Spotify desktop app installed.

## CLI

```bash
MUSIC="python3 ~/.claude/skills/music-control/scripts/music_cli.py"

$MUSIC [--provider kugou|spotify] <command>
```

| Command | Description |
|---------|-------------|
| `status` | Current track info (JSON) |
| `play` | Toggle play/pause |
| `next` | Skip to next |
| `prev` | Previous track |
| `play-by <title> [artist]` | Search and play immediately |
| `search <query>` | Search, returns list |
| `recommend <mood>` | Pick by mood and play |

`--provider` defaults to `kugou`. Set `MUSIC_PROVIDER=spotify` to default to Spotify.

## Mood Keywords

| Mood | When to use |
|------|-------------|
| `focused` | Deep work, coding in flow, reading |
| `relaxed` | Casual chat, breaks, light tasks |
| `hyped` | Feature shipped, bug fixed, wins |
| `sad` | User venting, stuck on a problem |
| `debug` | Frustrated, chasing a tricky bug |

## Proactive Trigger Rules

**Always act without being asked when you detect:**

| Signal in conversation | Action |
|------------------------|--------|
| User starts a new coding session | `recommend focused` → play top result |
| User says they fixed a bug / shipped | `recommend hyped` → play top result |
| User is frustrated / stuck | `recommend debug` |
| User mentions needing to relax | `recommend relaxed` |
| User mentions a specific song or artist | `play-by <song> <artist>` |
| Long silence / idle in conversation | `recommend relaxed` |
| User asks "play something" with no detail | Infer from recent conversation mood |

**When user specifies a song:**
```bash
# User: "play Sunny Day by Jay Chou"
$MUSIC play-by 晴天 周杰伦

# Verify it started
sleep 2 && $MUSIC status
```

**When inferring from context:**
```bash
# Detect mood → recommend → play top result automatically
$MUSIC --provider spotify recommend focused
```

## Response Format

```json
{"ok": true, "title": "晴天", "artist": "周杰伦", "playing": true}   // status
{"ok": true, "results": [{"title":"...", "artist":"...", "id":"..."}]} // search
{"ok": true, "action": "next"}                                         // control
{"ok": false, "error": "no_player", "message": "..."}                 // error
```

## Notes

- Spotify: search uses KuGou API under the hood (no Premium needed), plays via `spotify:search:` URI
- KuGou: requires KuGou Music macOS app installed
- If `status` returns `no_player`, the app may still be loading — wait 3s and retry
