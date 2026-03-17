#!/usr/bin/env bash
# 将 docs/.env.platform 中的端口配置同步到 art-design-pro/.env.development
# 用于手动运行 pnpm dev 时，确保 VITE_API_PROXY_URL 与 BACKEND_PORT 一致
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.platform"
FRONTEND_ENV="${PROJECT_ROOT}/art-design-pro/.env.development"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[sync_ports] ${ENV_FILE} not found, skip"
  exit 0
fi

source "${ENV_FILE}"
BACKEND_PORT="${BACKEND_PORT:-8989}"
NEW_URL="http://127.0.0.1:${BACKEND_PORT}"

if [[ -f "${FRONTEND_ENV}" ]]; then
  if grep -q "^VITE_API_PROXY_URL=" "${FRONTEND_ENV}"; then
    sed -i "s|^VITE_API_PROXY_URL=.*|VITE_API_PROXY_URL = ${NEW_URL}|" "${FRONTEND_ENV}"
    echo "[sync_ports] Updated VITE_API_PROXY_URL to ${NEW_URL} in ${FRONTEND_ENV}"
  else
    echo "VITE_API_PROXY_URL = ${NEW_URL}" >> "${FRONTEND_ENV}"
    echo "[sync_ports] Added VITE_API_PROXY_URL to ${FRONTEND_ENV}"
  fi
else
  echo "[sync_ports] ${FRONTEND_ENV} not found, skip"
fi
