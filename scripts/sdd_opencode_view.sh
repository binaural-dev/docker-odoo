#!/usr/bin/env bash
# sdd_opencode_view.sh — open a separate OS terminal window attached to a
# job's tmux session (dispatched by sdd_opencode_run.sh), so the user can
# watch the agent work live without taking over the terminal they're using
# to talk to Claude Code.
#
# Purely a visual convenience: sdd_opencode_status.sh remains the source of
# truth for status polling (sdd-lead/sdd-judge consume that, not this).
#
# Usage: bash sdd_opencode_view.sh <job_id> [terminal]
#   terminal defaults to $SDD_TMUX_TERMINAL, else autodetected from PATH.
#
# Configuration (shell profile / .env, no new config format):
#   SDD_TMUX_TERMINAL   — force a specific terminal emulator (e.g. "kitty")
#   SDD_TMUX_AUTO_VIEW   — read by sdd_opencode_run.sh, not this script, to
#                          decide whether to call this automatically on dispatch

set -euo pipefail

JOB_ID="${1:-}"
TERMINAL_OVERRIDE="${2:-${SDD_TMUX_TERMINAL:-}}"

if [[ -z "$JOB_ID" ]]; then
  printf '{"error":"no job_id","status":"failed"}\n'
  exit 1
fi

TMUX_SOCKET="/tmp/sdd-tmux/sdd.sock"
ATTACH_CMD="tmux -S $TMUX_SOCKET attach -t $JOB_ID"

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  printf '{"job":"%s","status":"skipped","reason":"no display","attach_cmd":"%s"}\n' \
    "$JOB_ID" "$ATTACH_CMD"
  exit 0
fi

# Candidates in autodetection order — first one found in PATH wins. Each
# maps to the invocation that runs a command and keeps the window open.
CANDIDATES=(gnome-terminal konsole xfce4-terminal kitty alacritty wezterm foot terminator xterm)

pick_terminal() {
  if [[ -n "$TERMINAL_OVERRIDE" ]]; then
    if command -v "$TERMINAL_OVERRIDE" >/dev/null 2>&1; then
      echo "$TERMINAL_OVERRIDE"
      return 0
    fi
    return 1
  fi
  for t in "${CANDIDATES[@]}"; do
    if command -v "$t" >/dev/null 2>&1; then
      echo "$t"
      return 0
    fi
  done
  return 1
}

TERM_BIN="$(pick_terminal || true)"

if [[ -z "$TERM_BIN" ]]; then
  printf '{"job":"%s","status":"skipped","reason":"no terminal found","attach_cmd":"%s"}\n' \
    "$JOB_ID" "$ATTACH_CMD"
  exit 0
fi

launch() {
  case "$TERM_BIN" in
    gnome-terminal)
      setsid gnome-terminal -- tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    konsole)
      setsid konsole -e tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    xfce4-terminal)
      setsid xfce4-terminal -e "tmux -S $TMUX_SOCKET attach -t $JOB_ID" >/dev/null 2>&1 &
      ;;
    kitty)
      setsid kitty tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    alacritty)
      setsid alacritty -e tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    wezterm)
      setsid wezterm start -- tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    foot)
      setsid foot tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    terminator)
      setsid terminator -x tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    xterm)
      setsid xterm -e tmux -S "$TMUX_SOCKET" attach -t "$JOB_ID" >/dev/null 2>&1 &
      ;;
    *)
      return 1
      ;;
  esac
  disown
}

if ! launch; then
  printf '{"job":"%s","status":"skipped","reason":"unsupported terminal: %s","attach_cmd":"%s"}\n' \
    "$JOB_ID" "$TERM_BIN" "$ATTACH_CMD"
  exit 0
fi

printf '{"job":"%s","status":"opened","terminal":"%s","attach_cmd":"%s"}\n' \
  "$JOB_ID" "$TERM_BIN" "$ATTACH_CMD"
