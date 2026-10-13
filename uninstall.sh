#!/bin/sh
# ============================================================
#  中国石油大学（北京）校园网 Srun 自动认证服务卸载脚本
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}正在停止并移除校园网 Srun 认证服务...${NC}"

# 1. 停止并禁用守护进程
if [ -f /etc/init.d/srun_webui ]; then
    /etc/init.d/srun_webui stop 2>/dev/null || true
    /etc/init.d/srun_webui disable 2>/dev/null || true
    rm -f /etc/init.d/srun_webui
    echo -e "${GREEN}✓ 已移除 WebUI 开机服务${NC}"
fi

# 2. 清理定时任务
CRON_FILE="/etc/crontabs/root"
if [ -f "${CRON_FILE}" ] && grep -q "srun_auth.py" "${CRON_FILE}"; then
    grep -v "srun_auth.py" "${CRON_FILE}" > "${CRON_FILE}.tmp" || true
    mv "${CRON_FILE}.tmp" "${CRON_FILE}"
    /etc/init.d/cron restart 2>/dev/null || true
    echo -e "${GREEN}✓ 已移除 Crontab 定时保活任务${NC}"
fi

# 3. 删除二进制与脚本
rm -f /usr/local/bin/srun_auth.py
rm -f /usr/local/bin/srun_webui.py
rm -f /var/log/srun_auth.log
echo -e "${GREEN}✓ 已清理 /usr/local/bin 脚本与运行日志${NC}"

# 4. 删除 LuCI 组件
rm -f /usr/lib/lua/luci/controller/srun.lua
rm -rf /usr/lib/lua/luci/view/srun
rm -f /tmp/luci-indexcache* /tmp/luci-modulecache* 2>/dev/null || true
echo -e "${GREEN}✓ 已移除 LuCI 控制器并清理缓存${NC}"

echo -e "\n${GREEN}卸载完成，所有组件已彻底清理。${NC}\n"
