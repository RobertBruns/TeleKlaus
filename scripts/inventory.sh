#!/usr/bin/env bash
# Run under the target account via bash -s -- dev|dispatcher.
set -u
role=${1:-}
case "$role" in
  dev|dispatcher) ;;
  *) printf '%s\n' 'Usage: inventory.sh dev|dispatcher' >&2; exit 2 ;;
esac

section() { printf '\n[%s]\n' "$1"; }
probe() {
  if ! "$@"; then
    printf 'Probe failed or unavailable: %s\n' "$1"
  fi
}

section 'Runtime'
probe date -u
probe uname -sr
probe python3 -c 'import sys, sqlite3, venv; print(sys.version); print("SQLite", sqlite3.sqlite_version)'
section 'Storage and account quota'
probe df -h "$HOME"
probe df -i "$HOME"
probe timeout -k 2 5 quota -s
section 'Process limits and host counters'
ulimit -a
probe nproc
probe free -m
if test -r /proc/self/limits; then cat /proc/self/limits; fi
section 'Cgroup membership and mount mapping'
if test -r /proc/self/cgroup; then cat /proc/self/cgroup; fi
awk '/ - cgroup2? /' /proc/self/mountinfo
# Walk visible v2 ancestors. A parent may impose a stricter shared limit.
cgroup=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
mount=$(awk '/ - cgroup2 / {print $5; exit}' /proc/self/mountinfo)
if test -n "$cgroup" && test -n "$mount" && test -d "${mount}${cgroup}"; then
  directory=${mount}${cgroup%/}
  while :; do
    printf '%s\n' "$directory"
    for metric in memory.max memory.high memory.current cpu.max cpuset.cpus.effective pids.max; do
      if test -r "$directory/$metric"; then
        printf '%s: ' "$metric"
        cat "$directory/$metric"
      fi
    done
    if test "$directory" = "$mount"; then break; fi
    directory=${directory%/*}
  done
else
  for controller in memory cpu pids cpuset; do
    group=$(awk -F: -v c="$controller" '$2 ~ ("(^|,)" c "(,|$)") {print $3; exit}' /proc/self/cgroup)
    mount=$(awk -v c="$controller" '$4 == "/" && / - cgroup / && $NF ~ ("(^|,)" c "(,|$)") {print $5; exit}' /proc/self/mountinfo)
    if test -z "$group" || test -z "$mount"; then continue; fi
    directory=${mount}${group%/}
    while :; do
      for metric in memory.limit_in_bytes memory.memsw.limit_in_bytes cpu.cfs_quota_us cpu.cfs_period_us pids.max cpuset.effective_cpus; do
        if test -r "$directory/$metric"; then printf '%s: ' "$directory/$metric"; cat "$directory/$metric"; fi
      done
      if test "$directory" = "$mount"; then break; fi
      directory=${directory%/*}
    done
  done
fi

section 'Supervisor, web routes and TCP listeners'
probe timeout -k 2 20 supervisorctl status
probe timeout -k 2 45 uberspace web domain list
probe timeout -k 2 45 uberspace web backend list
if command -v ss >/dev/null; then probe ss -ltn; else probe netstat -lnt; fi
section 'Outbound HTTPS'
if test "$role" = dev; then
  endpoint=https://api.anthropic.com/
else
  endpoint=https://api.development.push.apple.com/
fi
probe curl --disable --head --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP %{http_code}, HTTP version %{http_version}\n' "$endpoint"

if test "$role" = dev; then
  section 'Claude Code and terminal process hierarchy'
  if command -v claude; then probe claude --version; fi
  ps -u "$(id -u)" -o pid,ppid,tty,comm |
    awk 'NR == 1 || $4 ~ /^(claude|node|tmux|screen|SCREEN|bash|zsh|sshd)/'
fi
