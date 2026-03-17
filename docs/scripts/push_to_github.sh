#!/bin/bash
# 推送到GitHub的脚本（脚本所在目录：docs/scripts/，项目根目录为 docs/../）

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# 配置Git用户信息
git config user.name "Viki-researcher"
git config user.email "964361584@qq.com"

# 添加远程仓库（如果尚未添加）
git remote add origin https://github.com/Viki-researcher/ComfyUI-datagenerate-platform.git 2>/dev/null || true

# 推送到GitHub
echo "正在推送到GitHub..."
git push -u origin master

if [ $? -eq 0 ]; then
    echo "推送成功！"
else
    echo "推送失败，请检查网络连接"
fi
