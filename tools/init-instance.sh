#!/usr/bin/env bash
# Initialize a private learner instance for primer.
#
# Scaffolds a local data directory from templates/learner/, makes it a git
# repo, and points this machine's config at it. It does NOT touch GitHub or
# assume any auth — the public core can't know how you want to host or sync
# your private data, so it prints the commands and lets you run them.
#
# Usage:
#   tools/init-instance.sh [DATA_DIR]
#
# DATA_DIR defaults to ~/primer-data. Pass a path to override (the path
# may differ per machine; the config is per-machine and never synced).

set -euo pipefail

REPO_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
TEMPLATE_DIR="$REPO_DIR/templates/learner"
DATA_DIR="${1:-$HOME/primer-data}"
CONFIG_DIR="$HOME/.config/primer"
CONFIG_FILE="$CONFIG_DIR/config"

if [[ ! -d "$TEMPLATE_DIR" ]]; then
  echo "error: $TEMPLATE_DIR not found — are you running from the core repo?" >&2
  exit 1
fi

# If the data dir already holds an instance (e.g. a clone on a second
# machine), don't scaffold — just point this machine's config at it. The
# data is the only irreplaceable part of the system; never overwrite it.
if [[ -e "$DATA_DIR/learner/profile.md" ]]; then
  echo "Existing instance detected at: $DATA_DIR"
  echo "Skipping scaffold — only pointing this machine's config at it."
  EXISTING_INSTANCE=1
else
  EXISTING_INSTANCE=0
  echo "Scaffolding instance at: $DATA_DIR"
  mkdir -p "$DATA_DIR/learner" "$DATA_DIR/lessons"

  # State lives under $DATA_DIR/learner/, lessons under $DATA_DIR/lessons/
  # (see SKILL.md $DATA_DIR resolution). Mirrors the public core's layout.
  cp "$TEMPLATE_DIR"/*.md "$DATA_DIR/learner/"

  # A private instance has nothing to hide from itself; keep editor/OS noise out, plus
  # derived build products. Lesson view pages regenerate from the artifact
  # (primer_view.py render), so syncing them would only produce merge noise. Note
  # lessons/**/*.STATE.md is deliberately NOT ignored — it is checkpoint state and must
  # cross machines (D-0021).
  cat > "$DATA_DIR/.gitignore" <<'GITIGNORE'
.DS_Store
*.swp
*.swo
.idea/
.vscode/

# Derived: regenerated from the lesson artifact by primer_view.py
lessons/**/*.view.html
GITIGNORE

  cat > "$DATA_DIR/README.md" <<'README'
# primer — private instance data

This is the *instance* of primer: your profile, depth markers,
calibration log, and lessons. It is private and is meant to be a private
git repo so it syncs across your machines.

The public core (the "class") lives separately and is pulled for updates.
This repo holds only your data. Run the intake interview to populate it:

    /primer init
README

  # git doesn't track empty dirs; keep lessons/ in the repo so clones have it.
  touch "$DATA_DIR/lessons/.gitkeep"

  git -C "$DATA_DIR" init -q
  git -C "$DATA_DIR" add -A
  git -C "$DATA_DIR" commit -q -m "Initialize primer instance from template"
  echo "Initialized git repo in $DATA_DIR"
fi

# Per-machine pointer. Don't clobber an existing one without telling the user.
mkdir -p "$CONFIG_DIR"
if [[ -f "$CONFIG_FILE" ]] && grep -q '^DATA_DIR=' "$CONFIG_FILE"; then
  existing="$(grep '^DATA_DIR=' "$CONFIG_FILE" | head -n1 | cut -d= -f2-)"
  if [[ "$existing" != "$DATA_DIR" ]]; then
    echo "note: $CONFIG_FILE already points at: $existing" >&2
    echo "      leaving it unchanged. Edit it by hand to repoint to $DATA_DIR." >&2
  fi
else
  printf 'DATA_DIR=%s\n' "$DATA_DIR" > "$CONFIG_FILE"
  echo "Wrote config: $CONFIG_FILE -> $DATA_DIR"
fi

if [[ "$EXISTING_INSTANCE" -eq 1 ]]; then
  cat <<NEXT

This machine is now pointed at your existing instance. You're ready:

  - If the profile is already populated, just start: /primer next
  - If this is a fresh template, run the intake interview: /primer init
NEXT
else
  cat <<NEXT

Instance scaffolded. Next steps (you run these — the core never calls GitHub):

  1. Create a PRIVATE remote and push (example with gh):
       gh repo create primer-data --private --source "$DATA_DIR" --remote origin --push

     Or with an existing remote:
       git -C "$DATA_DIR" remote add origin <your-private-repo-url>
       git -C "$DATA_DIR" push -u origin main

  2. On a second machine: clone that private repo, then run
       tools/init-instance.sh <path-to-your-clone>
     to point that machine's config at it (it won't overwrite existing data).

  3. Run the intake interview to build your profile:
       /primer init
NEXT
fi
