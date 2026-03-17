#!/usr/bin/env bash
# ============================================================================
# 停止平台所有服务（前端、后端、ComfyUI 实例、标注服务实例）
#
# 端口配置从 docs/.env.platform 读取（单一事实源），若文件不存在则使用默认端口
# 停止策略：
#   1. 先停 ComfyUI / 标注实例（按端口范围批量查找）
#   2. 再停后端 / 前端主服务
#   3. 每个服务：先查 PID 文件 → 再查端口 → 确保彻底停止
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PID_DIR="${ROOT_DIR}/runtime/pids"
ENV_FILE="${ROOT_DIR}/.env.platform"

# 加载端口配置（单一事实源）
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

# 解析端口范围 "8200-8299" -> start end
_parse_port_range() {
  local range="${1:-8200-8299}"
  if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
  else
    echo "8200 8299"
  fi
}

read -r COMFYUI_START COMFYUI_END <<< "$(_parse_port_range "${COMFYUI_PORT_RANGE:-8200-8299}")"
read -r ANNOTATION_START ANNOTATION_END <<< "$(_parse_port_range "${ANNOTATION_PORT_RANGE:-7860-7899}")"

BACKEND_PORT="${BACKEND_PORT:-8989}"
FRONTEND_PORT="${FRONTEND_PORT:-3006}"

_kill_pid() {
  local pid="$1"
  local timeout="${2:-10}"
  kill -TERM "-${pid}" >/dev/null 2>&1 || kill -TERM "${pid}" >/dev/null 2>&1 || true
  for _ in $(seq 1 "${timeout}"); do
    kill -0 "${pid}" >/dev/null 2>&1 || return 0
    sleep 1
  done
  kill -KILL "-${pid}" >/dev/null 2>&1 || kill -KILL "${pid}" >/dev/null 2>&1 || true
}

stop_by_pid_or_port() {
  local name="$1"
  local port="$2"
  local pidfile="${PID_DIR}/${name}.pid"

  # 第一步：从 PID 文件停止
  if [[ -f "${pidfile}" ]]; then
    local file_pid
    file_pid="$(cat "${pidfile}" || true)"
    rm -f "${pidfile}"
    if [[ -n "${file_pid}" ]] && kill -0 "${file_pid}" >/dev/null 2>&1; then
      echo "[stop_all] stopping ${name} via pidfile (pid=${file_pid}) ..."
      _kill_pid "${file_pid}" 10
    fi
  fi

  # 第二步：从端口查找并停止（覆盖非 start_all.sh 启动的场景）
  if [[ -n "${port}" ]]; then
    local port_pids
    port_pids="$(lsof -ti:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "${port_pids}" ]]; then
      for pp in ${port_pids}; do
        echo "[stop_all] stopping ${name} on port ${port} (pid=${pp}) ..."
        _kill_pid "${pp}" 10
      done
    fi
  fi

  # 最终确认
  local remaining
  remaining="$(lsof -ti:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "${remaining}" ]]; then
    echo "[stop_all] ${name}: stopped"
  else
    echo "[stop_all] ${name}: WARNING - port ${port} still occupied by pid=${remaining}"
  fi
}

stop_port_range() {
  local name="$1"
  local range_start="$2"
  local range_end="$3"
  local pids
  pids="$(lsof -ti:"${range_start}-${range_end}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "${pids}" ]]; then
    echo "[stop_all] ${name}: none running"
    return 0
  fi
  for pid in ${pids}; do
    echo "[stop_all] stopping ${name} (pid=${pid}) ..."
    _kill_pid "${pid}" 5
  done
  echo "[stop_all] ${name}: done"
}

# 1) 先停子服务
stop_port_range "comfyui instances" "${COMFYUI_START}" "${COMFYUI_END}"
stop_port_range "annotation instances" "${ANNOTATION_START}" "${ANNOTATION_END}"

# 2) 再停主服务
stop_by_pid_or_port "backend" "${BACKEND_PORT}"
stop_by_pid_or_port "frontend" "${FRONTEND_PORT}"

echo "[stop_all] all services stopped"
