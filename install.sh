#!/bin/sh
# ============================================================
#  中国石油大学（北京）校园网 Srun 自动认证与 WebUI 一键安装脚本
#  适用于: OpenWrt / iStoreOS 等固件
# ============================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  中国石油大学（北京）校园网 Srun 自动认证服务安装程序${NC}"
echo -e "${BLUE}============================================================${NC}"

# 1. 检查 Python3 环境
echo -e "\n${YELLOW}[1/6] 检查 Python3 运行环境...${NC}"
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}未检测到 python3，尝试通过 opkg 自动安装...${NC}"
    opkg update || true
    opkg install python3 || {
        echo -e "${RED}[ERROR] python3 安装失败，请先手动运行 opkg install python3 后重试。${NC}"
        exit 1
    }
fi
echo -e "${GREEN}✓ Python3 检查通过: $(python3 --version)${NC}"

# 2. 获取脚本所在根目录
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# 3. 安装认证核心脚本
echo -e "\n${YELLOW}[2/4] 部署认证核心脚本...${NC}"
mkdir -p /usr/local/bin
cp -f "${BASE_DIR}/bin/srun_auth.py" /usr/local/bin/srun_auth.py
chmod +x /usr/local/bin/srun_auth.py
echo -e "${GREEN}✓ 已安装: /usr/local/bin/srun_auth.py${NC}"

# 4. 部署 LuCI 界面组件
echo -e "\n${YELLOW}[3/4] 部署 LuCI 路由器管理界面集成...${NC}"
mkdir -p /usr/lib/lua/luci/controller
mkdir -p /usr/lib/lua/luci/view/srun
cp -f "${BASE_DIR}/luci/controller/srun.lua" /usr/lib/lua/luci/controller/srun.lua
cp -f "${BASE_DIR}/luci/view/srun/index.htm" /usr/lib/lua/luci/view/srun/index.htm
echo -e "${GREEN}✓ 已安装 LuCI 控制器与视图模板${NC}"

# 5. 配置后台定时检测与自动保活任务 (默认每 2 分钟)
echo -e "\n${YELLOW}[4/4] 配置后台定时重连保活任务 (Cron)...${NC}"
CRON_FILE="/etc/crontabs/root"
mkdir -p /etc/crontabs
touch "${CRON_FILE}"

# 清理旧的重复任务
if grep -q "srun_auth.py" "${CRON_FILE}"; then
    grep -v "srun_auth.py" "${CRON_FILE}" > "${CRON_FILE}.tmp" || true
    mv "${CRON_FILE}.tmp" "${CRON_FILE}"
fi

# 写入新的每2分钟保活任务
echo "*/2 * * * * /usr/bin/python3 /usr/local/bin/srun_auth.py >/dev/null 2>&1" >> "${CRON_FILE}"
/etc/init.d/cron restart 2>/dev/null || true
echo -e "${GREEN}✓ 定时任务已启用（每 2 分钟自动检测断线重连）${NC}"

# 6. 重建 LuCI 索引缓存
echo -e "\n${YELLOW}刷新 LuCI 菜单缓存...${NC}"
rm -f /tmp/luci-indexcache* /tmp/luci-modulecache* 2>/dev/null || true
echo -e "${GREEN}✓ 菜单缓存刷新完成${NC}"

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}🎉 恭喜！校园网 Srun 自动认证服务已成功安装！${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "你可以通过以下方式配置学号与密码："
echo -e " 1. ${BLUE}LuCI 管理页面${NC}: http://<路由器IP> -> 服务 -> 校园网认证"
echo -e " 2. ${BLUE}终端手动配置${NC}: 编辑 /usr/local/bin/srun_auth.py"
echo -e "============================================================\n"
