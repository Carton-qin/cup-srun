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

# 3. 安装认证脚本与 WebUI 后台
echo -e "\n${YELLOW}[2/6] 部署认证核心与独立 WebUI...${NC}"
mkdir -p /usr/local/bin
cp -f "${BASE_DIR}/bin/srun_auth.py" /usr/local/bin/srun_auth.py
cp -f "${BASE_DIR}/bin/srun_webui.py" /usr/local/bin/srun_webui.py
chmod +x /usr/local/bin/srun_auth.py
chmod +x /usr/local/bin/srun_webui.py
echo -e "${GREEN}✓ 已安装: /usr/local/bin/srun_auth.py${NC}"
echo -e "${GREEN}✓ 已安装: /usr/local/bin/srun_webui.py${NC}"

# 4. 部署 procd 守护服务
echo -e "\n${YELLOW}[3/6] 配置 WebUI 开机自启服务...${NC}"
cp -f "${BASE_DIR}/etc/init.d/srun_webui" /etc/init.d/srun_webui
chmod +x /etc/init.d/srun_webui
/etc/init.d/srun_webui enable
/etc/init.d/srun_webui restart
echo -e "${GREEN}✓ WebUI 服务已启动并设置开机自启 (监听端口: 8880)${NC}"

# 5. 部署 LuCI 界面组件
echo -e "\n${YELLOW}[4/6] 部署 LuCI 路由器管理界面集成...${NC}"
mkdir -p /usr/lib/lua/luci/controller
mkdir -p /usr/lib/lua/luci/view/srun
cp -f "${BASE_DIR}/luci/controller/srun.lua" /usr/lib/lua/luci/controller/srun.lua
cp -f "${BASE_DIR}/luci/view/srun/index.htm" /usr/lib/lua/luci/view/srun/index.htm
echo -e "${GREEN}✓ 已安装 LuCI 控制器与视图模板${NC}"

# 6. 配置后台定时检测与自动保活任务 (默认每 2 分钟)
echo -e "\n${YELLOW}[5/6] 配置后台定时重连保活任务 (Cron)...${NC}"
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

# 7. 重建 LuCI 索引缓存
echo -e "\n${YELLOW}[6/6] 刷新 LuCI 菜单缓存...${NC}"
rm -f /tmp/luci-indexcache* /tmp/luci-modulecache* 2>/dev/null || true
echo -e "${GREEN}✓ 菜单缓存刷新完成${NC}"

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}🎉 恭喜！校园网 Srun 自动认证服务已成功安装！${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "你可以通过以下任意方式配置学号与密码："
echo -e " 1. ${BLUE}独立 WebUI${NC}  : http://<路由器IP>:8880"
echo -e " 2. ${BLUE}LuCI 管理页面${NC}: http://<路由器IP> -> 服务 -> 校园网认证"
echo -e " 3. ${BLUE}终端手动配置${NC}: 编辑 /usr/local/bin/srun_auth.py"
echo -e "============================================================\n"
