#!/bin/bash
# 推送到Gitee的脚本（脚本所在目录：docs/scripts/，项目根目录为 docs/../）

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# 添加Gitee远程仓库
git remote add gitee https://gitee.com/akaizi/ComfyUI-datagenerate-platform.git 2>/dev/null || true

# 推送到Gitee
echo "正在推送到Gitee..."
git push -u gitee master
