# CUP Srun Campus Network Auto-Auth for OpenWrt / iStoreOS
### 中国石油大学（北京）校园网 Srun 自动认证与 LuCI 管理插件

[![OpenWrt](https://img.shields.io/badge/Platform-OpenWrt%20%7C%20iStoreOS-blue.svg)](https://openwrt.org/)
[![Python](https://img.shields.io/badge/Python-3.x-brightgreen.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

专为部署在 **OpenWrt / iStoreOS** 等软路由与 Linux 网关设备的深澜（Srun3000 / Srun4000）校园网自动登录、后台保活与可视化管理插件。

解决校园网频繁掉线、设备数限制、重启软路由无法联网等痛点。全屋设备通过路由器连网，统一走软路由自动认证出网。

---

## 🌟 特性一览

- ⚡ **无感自动登录**：开机自动认证，网络掉线或注销后定时任务秒级探测并自动重连。
- 🖥️ **原生 LuCI 界面管理**：无缝融入 iStoreOS / OpenWrt 路由器后台（`服务 -> 校园网认证`），受路由 root 账户保护，安全可靠。
- 🚪 **全流程生命周期管理**：支持在线状态实时监测、一键立即认证、一键注销下线。
- ⚙️ **动态配置即时生效**：Web 界面随时修改学号、密码与检测频率，即刻生效写入底层脚本。
- 🛡️ **轻量安全与内存保护**：纯 Python 标准库编写（无需额外 pip 依赖）；内置 500 行日志滚动保护，防止 OpenWrt 内存盘（tmpfs）占满。
- 📦 **开箱即用一键脚本**：提供一键安装与卸载 Shell 脚本，一键完成 Crontab 定时保活注册与 LuCI 菜单挂载。

---

## 🚀 快速安装部署

### 方式 1：一键快速安装（推荐）

通过 SSH 登录到你的 OpenWrt / iStoreOS 路由器终端，执行以下命令（内置自动下载与环境检测，**无需安装 git**）：

```bash
curl -sLk https://github.com/Carton-qin/cup-srun/archive/refs/heads/main.tar.gz | tar -xz -C /tmp
cd /tmp/cup-srun-main
chmod +x install.sh
./install.sh
```

> [!TIP]
> - 若你的路由器已自行安装 `git`，也可直接通过 `git clone https://github.com/Carton-qin/cup-srun.git /tmp/cup-srun && cd /tmp/cup-srun && chmod +x install.sh && ./install.sh` 进行安装。
> - 安装脚本会自动检测 `python3` 环境；若缺少将自动通过 `opkg` 尝试安装。

---

### 方式 2：手动部署

如果你更倾向于手动分步部署，可将项目文件拷贝至对应路径：

```bash
# 1. 复制核心程序
mkdir -p /usr/local/bin
cp bin/srun_auth.py /usr/local/bin/srun_auth.py
chmod +x /usr/local/bin/srun_auth.py

# 2. 部署 LuCI 界面组件
mkdir -p /usr/lib/lua/luci/controller
mkdir -p /usr/lib/lua/luci/view/srun
cp luci/controller/srun.lua /usr/lib/lua/luci/controller/srun.lua
cp luci/view/srun/index.htm /usr/lib/lua/luci/view/srun/index.htm
rm -f /tmp/luci-indexcache*

# 3. 配置后台保活定时任务 (每2分钟检测一次)
(crontab -l 2>/dev/null | grep -v "srun_auth.py"; echo "*/2 * * * * /usr/bin/python3 /usr/local/bin/srun_auth.py >/dev/null 2>&1") | crontab -
/etc/init.d/cron restart
```

---

## 📖 使用指南

### 1. LuCI 管理界面
登录 iStoreOS / OpenWrt 路由器后台，点击左侧导航栏：
```text
服务 -> 校园网认证
```
- **状态卡片**：实时显示在线状态、当前分配的内网 IP、已登录用户名。
- **手动操作**：支持「🔑 立即认证」、「🚪 注销下线」、「🔄 刷新状态」。
- **账号配置**：输入学号与校园网密码，点击「💾 保存配置」即刻写入底层脚本生效。
- **定时任务设置**：可开启/关闭后台保活检测，并自定义检测频率（1~1440 分钟）。
- **实时日志**：一键刷新查看认证与保活日志。

### 2. 命令行（CLI）调试
你也可以直接在 SSH 终端通过命令行与认证核心交互：

```bash
# 检查当前网络状态（返回 ONLINE <用户名> <IP> 或 OFFLINE）
python3 /usr/local/bin/srun_auth.py --status

# 主动注销当前设备下线
python3 /usr/local/bin/srun_auth.py --logout

# 运行一次检测与自动保活登录
python3 /usr/local/bin/srun_auth.py

# 查看实时运行日志
tail -f /var/log/srun_auth.log
```

---

## 📂 仓库目录结构

```text
.
├── README.md               # 项目主说明文档
├── LICENSE                 # MIT 开源授权协议
├── install.sh              # 一键自动安装脚本
├── uninstall.sh            # 一键完全卸载脚本
├── bin/
│   └── srun_auth.py        # 认证核心引擎（加解密、保活与状态探测、注销下线）
├── luci/
│   ├── controller/
│   │   └── srun.lua        # LuCI 路由与后端逻辑控制器
│   └── view/
│       └── srun/
│           └── index.htm   # LuCI 卡片式响应式前端页面
└── docs/
    └── protocol.md         # 深澜 Srun 协议分析与加密细节技术备忘
```

---

## 🗑️ 卸载

若需彻底清理并移除该认证服务，只需执行：

```bash
chmod +x uninstall.sh
./uninstall.sh
```

---

## 📄 协议解析与技术备忘

深澜 Srun Portal 的加密过程涉及：
1. 动态获取 Challenge Token 作为 Nonce 盐值；
2. 采用类 XXTEA 变种对称分组加密算法（`xencode`）加密用户信息字典，再经特殊字符表的自定义 Base64 编码构造 `{SRBX1}` 串；
3. 密码经 HMAC-MD5 加密；
4. 拼接 Token、用户名、密码摘要、IP、acid 等字段计算 SHA1 校验和。

详细的前端逆向与协议分析可参考 [docs/protocol.md](docs/protocol.md)。

---

## ⚠️ 免责声明

1. 本项目仅供网络技术学习、软路由运维研究以及校园网网络连通性优化使用。
2. 请遵守中国石油大学（北京）校园网网络安全与使用规范，严禁用于任何破坏网络秩序或非法用途。

---

## 📜 许可证

本项目采用 [MIT License](LICENSE) 开源。欢迎提交 Issue 与 Pull Request！
