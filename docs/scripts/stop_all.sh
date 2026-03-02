#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${ROOT_DIR}/runtime/pids"

stop_one() {
  local name="$1"
  local port="$2"
  local pidfile="${PID_DIR}/${name}.pid"
  local pid=""

  # 1) 优先从 pidfile 获取
  if [[ -f "${pidfile}" ]]; then
    pid="$(cat "${pidfile}" || true)"
    if [[ -n "${pid}" ]] && ! kill -0 "${pid}" >/dev/null 2>&1; then
      pid=""
      rm -f "${pidfile}"
    fi
  fi

  # 2) pidfile 无效时，从端口查找进程
  if [[ -z "${pid}" && -n "${port}" ]]; then
    pid="$(lsof -ti:${port} 2>/dev/null | head -1 || true)"
  fi

  if [[ -z "${pid}" ]]; then
    echo "[stop_all] ${name}: not running"
    rm -f "${pidfile}"
    return 0
  fi

  echo "[stop_all] stopping ${name} (pid=${pid}) ..."
  kill -TERM "-${pid}" >/dev/null 2>&1 || kill -TERM "${pid}" >/dev/null 2>&1 || true

  for _ in {1..30}; do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      echo "[stop_all] ${name}: stopped"
      rm -f "${pidfile}"
      return 0
    fi
    sleep 1
  done

  echo "[stop_all] ${name}: force kill (pid=${pid})"
  kill -KILL "-${pid}" >/dev/null 2>&1 || kill -KILL "${pid}" >/dev/null 2>&1 || true
  rm -f "${pidfile}"
}

stop_one "frontend" "3006"
stop_one "backend" "9999"
