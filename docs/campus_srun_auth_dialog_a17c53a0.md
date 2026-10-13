# 对话记录归档：校园网自动认证服务排查与修复 (a17c53a0-6109-4f6f-a02b-24d390f0003a)

> **对话 ID**：`a17c53a0-6109-4f6f-a02b-24d390f0003a`  
> **对话主题**：Debugging Campus Network Login Service (调试校园网登录认证服务)  
> **时间**：2026-10-13 14:26 ~ 15:20  
> **目标主机**：iStoreOS（中国石油大学（北京）校园网环境）  
> **当前归档工程**：`istoreos-university`

---

## 一、 背景与用户初始问题

用户在全新安装的 iStoreOS 小主机上，使用 Python 编写了一个校园网 Srun3000（深澜）自动认证登录脚本，部署于 `/usr/local/bin/srun_auth.py`，但在实际运行时报错无法上网。

查看运行日志 `/var/log/srun_auth.log` 显示：
```text
[*] 未认证，开始登录...
[-] 认证失败: sign_error
```

---

## 二、 问题根因排查与协议分析

通过反编译与分析中国石油大学（北京）深澜认证网关（`https://login.cup.edu.cn/static/themes/pro/js/Portal.js`）的前端认证逻辑，定位到以下两个关键 Bug：

### 1. 核心 Bug：校验和（`chksum`）计算多加了 `"{MD5}"` 前缀
- **原代码错误**：
  ```python
  # 错误写法：在拼装 SHA1 待签名字串时加入了 "{MD5}" 标识
  chk_str = (token + USERNAME + token + "{MD5}" + hmd5 +
             token + AC_ID + token + ip +
             token + "200" + token + "1" + token + info_encoded)
  chksum = sha1(chk_str)
  ```
- **实际协议规则**：
  - 前端 JS 逻辑中：`var hmd5 = md5(password, token); str += token + hmd5;`
  - 参与 `chksum`（SHA1）签名的**必须是纯密文 `hmd5`**，绝不能包含 `"{MD5}"`。
  - `"{MD5}"` 前缀**仅在最终向 `/cgi-bin/srun_portal` 发送登录请求**的 `password` 参数时才需要携带。

### 2. 定时任务频率错误（Cron 表达式）
- **原 Crontab**：`0 */10 * * *`（实际为**每 10 小时**执行一次，而非每 10 分钟）。
- **修正为**：`*/10 * * * *`（每 10 分钟检测一次，断网自动重登）。

---

## 三、 修复后的完整认证脚本

项目工程中已同步落地以下两个脚本：
1. **[`srun_auth_fixed.py`](file:///Users/gaojia/Documents/istoreos-university/srun_auth_fixed.py)**：修复后的纯净单文件 Srun3000 认证脚本。
2. **[`srun_auth_deploy.py`](file:///Users/gaojia/Documents/istoreos-university/srun_auth_deploy.py)**：支持一键远程 SSH 部署至软路由的自动化脚本。

### 关键加密流程对照表：

```text
1. 获取 Challenge Token:
   GET https://login.cup.edu.cn/cgi-bin/get_challenge -> 获取 token 和 client_ip

2. 用户信息对称加密 (info):
   info_raw = {"username": ..., "password": ..., "ip": client_ip, "acid": "1", "enc_ver": "srun_bx1"}
   info_encoded = "{SRBX1}" + fkbase64(xencode(info_raw, token))

3. 密码 HMAC-MD5 计算:
   hmd5 = hmac_md5(PASSWORD, token)

4. 构造 chksum 签名（无 {MD5} 标识）:
   chk_str = token + USERNAME + token + hmd5 + token + AC_ID + token + ip + token + "200" + token + "1" + token + info_encoded
   chksum = sha1(chk_str)

5. 发送 Portal 登录认证:
   GET https://login.cup.edu.cn/cgi-bin/srun_portal
   参数中 password = "{MD5}" + hmd5, chksum = chksum, info = info_encoded
```

---

## 四、 iStoreOS 部署与连通性验证

部署到 iStoreOS 并测试运行后，输出：
```text
[+] 认证成功！IP: 10.4.18.189
```
外网访问恢复正常，Ping 延迟降至 2~4ms。

---

## 五、 IPv6 公网连通性检测结果

在该对话的第二阶段，对主机的 IPv6 支持情况进行了系统探测：
1. **WAN 原生公网 IPv6**：`2001:da8:258:6403:.../64`（中国教育和科研计算机网 CERNET2 全球单播公网 IP）。
2. **外网实际出口 IPv6**：`240e:604:20c:3200::...`（电信 IPv6 优质出口）。
3. **延迟测试**：直连清华镜像源 CERNET IPv6 节点延迟低至 **2.3 ms**，丢包率 0%。
