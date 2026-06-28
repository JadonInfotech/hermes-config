# Windows Hermes Config Path Discovery

## The Problem

Docs and examples say `~/.hermes` but on Windows Hermes Desktop,
this path **does not exist**. The actual location is different.

## Verified Discovery Method

### Step 1: Check the HERMES_HOME environment variable

```bash
echo $HERMES_HOME
# On Windows Hermes Desktop: C:\Users\<user>\AppData\Local\hermes
```

### Step 2: Use Hermes commands (preferred — always correct)

```bash
hermes config path      # prints the actual config.yaml location
hermes config env-path  # prints the .env location
```

### Step 3: Manual inspection (if commands not available)

On Hermes Desktop for Windows, check:
```
C:\Users\<user>\AppData\Local\hermes\
```

## Why the Path is Different

- **Hermes Desktop installer** for Windows stores config in `AppData\Local\hermes`
- **Standalone/portable installs** (via install script on Unix/macOS/WSL) use `~/.hermes`
- The `HERMES_HOME` env var is set by the Hermes Desktop installer to the Windows path

## Converting Between Path Formats

### Windows (in git-bash/MSYS terminal):
| What | Path |
|------|------|
| Config dir | `/c/Users/<user>/AppData/Local/hermes` |
| .env file | `/c/Users/<user>/AppData/Local/hermes/.env` |
| Skills | `/c/Users/<user>/AppData/Local/hermes/skills/` |

### Windows (in PowerShell/CMD):
| What | Path |
|------|------|
| Config dir | `C:\Users\<user>\AppData\Local\hermes` |
| .env file | `C:\Users\<user>\AppData\Local\hermes\.env` |
| Skills | `C:\Users\<user>\AppData\Local\hermes\skills\` |

### Unix/macOS/WSL:
| What | Path |
|------|------|
| Config dir | `~/.hermes` |
| .env file | `~/.hermes/.env` |
| Skills | `~/.hermes/skills/` |

## Key Finding from Session

When user said `cd ~/.hermes` didn't work on Windows:
- The error was: "The system cannot find the path specified"
- Root cause: path doesn't exist on Windows Hermes Desktop
- Fix: use `cd /c/Users/<user>/AppData/Local/hermes` in git-bash
- Or better: always use `hermes config path` to get the real path

## SSH Key Location

SSH keys are stored at `~/.ssh/` which on Windows git-bash resolves to:
```
C:\Users\<user>\.ssh\
```

This path is consistent across Windows — SSH config always lives here,
independent of where Hermes is installed.
