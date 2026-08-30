#!/usr/bin/env bash
set -u

input=$(cat)

get() { printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null; }

dir=$(get '.workspace.current_dir // .cwd')
model=$(get '.model.display_name')
cost=$(get '.cost.total_cost_usd')
ctx_used=$(get '.context_window.used_percentage')
ctx_in=$(get '.context_window.total_input_tokens')
ctx_out=$(get '.context_window.total_output_tokens')
ctx_size=$(get '.context_window.context_window_size')
h5_pct=$(get '.rate_limits.five_hour.used_percentage')
h5_reset=$(get '.rate_limits.five_hour.resets_at')
d7_pct=$(get '.rate_limits.seven_day.used_percentage')
fast=$(get '.fast_mode')

[ -z "$dir" ] && dir=$PWD

pretty=$(printf '%s' "$dir" | sed "s|^$HOME|~|" |
  awk -F/ '{ if (NF > 3) printf "…/%s/%s/%s", $(NF-2), $(NF-1), $NF; else printf "%s", $0 }')

branch=$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null ||
  git -C "$dir" rev-parse --short HEAD 2>/dev/null)
dirty=""
if [ -n "$branch" ] && [ -n "$(git -C "$dir" status --porcelain 2>/dev/null)" ]; then
  dirty="*"
fi

FG0='251;241;199'
ORANGE='214;93;14'
YELLOW='215;153;33'
AQUA='104;157;106'
BLUE='69;133;136'
PURPLE='177;98;134'
BG1='60;56;54'
GREEN='152;151;26'
RED='204;36;29'

fg() { printf '\033[38;2;%sm' "$1"; }
bg() { printf '\033[48;2;%sm' "$1"; }
rst=$'\033[0m'
sep=$''
sep_thin=$''
cap_l=$''
cap_r=$''

seg() {
  if [ "$1" = "$prev" ]; then
    out+=$(bg "$1")$(fg "$FG0")$sep_thin
  else
    out+=$(bg "$1")$(fg "$prev")$sep
  fi
  out+=$(bg "$1")$(fg "$FG0")" $2 "
  prev=$1
}

heat() {
  if [ "$1" -ge 85 ]; then printf '%s' "$RED"
  elif [ "$1" -ge 60 ]; then printf '%s' "$YELLOW"
  else printf '%s' "$GREEN"; fi
}

human() {
  awk -v n="$1" 'BEGIN {
    if (n >= 1000000) printf "%.1fM", n/1000000
    else if (n >= 1000) printf "%.0fk", n/1000
    else printf "%d", n
  }'
}

until_reset() {
  awk -v t="$1" -v now="$(date +%s)" 'BEGIN {
    d = t - now
    if (d < 0) d = 0
    h = int(d/3600); m = int((d%3600)/60)
    if (h > 0) printf "%dh%02dm", h, m
    else printf "%dm", m
  }'
}

out=""
prev=$ORANGE
out+=$(fg "$ORANGE")$cap_l
out+=$(bg "$ORANGE")$(fg "$FG0")" ✳ "

seg "$YELLOW" "$pretty"
[ -n "$branch" ] && seg "$AQUA" "$(printf '') $branch$dirty"

if [ -n "$model" ]; then
  label=$model
  [ "$fast" = "true" ] && label="$(printf '\U000f04c5') $model"
  seg "$BLUE" "$label"
fi

if [ -n "$ctx_used" ]; then
  tok=$(human "$((${ctx_in:-0} + ${ctx_out:-0}))")
  win=$(human "${ctx_size:-0}")
  seg "$(heat "$ctx_used")" "$(printf '\U000f035b') $tok/$win ${ctx_used}%"
fi

if [ -n "$h5_pct" ]; then
  label="5h ${h5_pct}%"
  [ -n "$h5_reset" ] && label="$label $(printf '↻')$(until_reset "$h5_reset")"
  seg "$(heat "$h5_pct")" "$label"
fi

[ -n "$d7_pct" ] && seg "$PURPLE" "7d ${d7_pct}%"

if [ -n "$cost" ]; then
  spend=$(printf '%.2f' "$cost" 2>/dev/null)
  [ -n "$spend" ] && [ "$spend" != "0.00" ] && seg "$BG1" "\$$spend"
fi

out+=$rst$(fg "$prev")$cap_r$rst
printf '%s\n' "$out"
