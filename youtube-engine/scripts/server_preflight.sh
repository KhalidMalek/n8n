#!/usr/bin/env bash
set -u

printf '\n=== AutoTube server preflight ===\n'
printf 'Date: '; date
printf 'Host: '; hostname
printf 'OS: '; (grep PRETTY_NAME /etc/os-release 2>/dev/null || true)
printf 'Kernel: '; uname -r
printf 'Arch: '; uname -m
printf '\n--- CPU ---\n'
(nproc && lscpu | grep -E 'Model name|CPU\(s\)|Architecture' | head -8) 2>/dev/null || true
printf '\n--- Memory ---\n'
free -h || true
printf '\n--- Disk ---\n'
df -h / /opt 2>/dev/null || df -h /
printf '\n--- Swap ---\n'
swapon --show || true
printf '\n--- Docker ---\n'
if command -v docker >/dev/null 2>&1; then
  docker --version
  docker compose version 2>/dev/null || echo 'Docker Compose plugin not found'
else
  echo 'Docker not installed'
fi
printf '\n--- Listening ports relevant to AutoTube ---\n'
ss -ltnp 2>/dev/null | grep -E ':(5678|8000)\b' || echo 'Ports 5678 and 8000 are free'
printf '\n--- Existing v8 service (read-only check) ---\n'
systemctl is-active v8-paper-bot.service 2>/dev/null || true
printf '\n--- Current load ---\n'
uptime
printf '\n=== End preflight ===\n'
