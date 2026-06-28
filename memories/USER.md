Jadon (JadonInfotech) uses GitHub sync for Hermes config across multiple machines. Repo: git@github.com:JadonInfotech/hermes-config.git. On second desktop, Hermes was running (multiple Hermes.exe processes) and held file locks on state.db/logs — had to ask user to close the app before git reset could work. Created skill: hermes-config-sync.
§
User has TWO Windows desktops (Desktop 1 + Desktop 2) with Hermes synced via GitHub repo: github.com/JadonInfotech/hermes-config. SSH key email: deepak.dhtml@gmail.com. Wants bidirectional session sync between machines so work on either desktop is preserved. Uses Hermes desktop app on Windows. Preferred workflow: run sync script BEFORE starting Hermes (closes with Ctrl+C or tray exit).
§
User: Jadon/JadonInfotech
GitHub: github.com/JadonInfotech/hermes-config
Email for git: jadonandcompany.in@gmail.com
SSH key email: deepak.dhtml@gmail.com
Has TWO Windows desktops they want to sync Hermes Agent between
Uses Git Bash terminal on Windows
Prefers bidirectional session sync (not one-way)
Challenges: SSH auth setup, git merge conflicts with logs, state.db locking when Hermes running
Hermes config synced via Git to avoid manual file copying