#!/usr/bin/env python3
# ============================================================
#  中国石油大学（北京）校园网 Srun 自动认证脚本
#  部署路径: /usr/local/bin/srun_auth.py
# ============================================================

import datetime
import hashlib
import hmac
import json
import math
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

# ==================== 配置区域（WebUI可通过正则动态修改） ====================
USERNAME = "YOUR_USERNAME"        # 校园网账号（学号，可通过 Web 界面修改）
PASSWORD = "YOUR_PASSWORD"        # 校园网密码（可通过 Web 界面修改）
SERVER   = "https://login.cup.edu.cn" # 认证网关地址
AC_ID    = "1"                    # AC_ID，通常为 1
# ==============================================================================

LOG_FILE = "/var/log/srun_auth.log"
MAX_LOG_LINES = 500

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"

def now_str():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg):
    line = f"{now_str()} {msg}"
    print(line)
    try:
        # 限制日志大小，防止 OpenWrt 内存盘 (tmpfs) 占满
        lines = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception:
                pass
        lines.append(line + "\n")
        if len(lines) > MAX_LOG_LINES:
            lines = lines[-MAX_LOG_LINES:]
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception:
        pass

def get(url, timeout=8):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
        return r.read().decode('utf-8', 'ignore')

def parse_json(text):
    m = re.search(r'\((.+)\)', text)
    return json.loads(m.group(1)) if m else {}

def get_base64(s):
    r = []
    x = len(s) % 3
    if x:
        s = s + '\0' * (3 - x)
    for i in range(0, len(s), 3):
        d = s[i:i + 3]
        a = ord(d[0]) << 16 | ord(d[1]) << 8 | ord(d[2])
        r.append(ALPHA[a >> 18])
        r.append(ALPHA[a >> 12 & 63])
        r.append(ALPHA[a >> 6 & 63])
        r.append(ALPHA[a & 63])
    if x == 1:
        r[-1] = '='
        r[-2] = '='
    elif x == 2:
        r[-1] = '='
    return ''.join(r)

def ordat(msg, idx):
    return ord(msg[idx]) if len(msg) > idx else 0

def sencode(msg, key):
    l = len(msg)
    pwd = []
    for i in range(0, l, 4):
        pwd.append(
            ordat(msg, i) | ordat(msg, i + 1) << 8 | ordat(msg, i + 2) << 16
            | ordat(msg, i + 3) << 24
        )
    if key:
        pwd.append(l)
    return pwd

def lencode(msg, key):
    l = len(msg)
    ll = (l - 1) << 2
    if key:
        m = msg[l - 1]
        if m < ll - 3 or m > ll:
            return ""
        ll = m
    res = []
    for i in range(0, l):
        res.append(
            chr(msg[i] & 0xff) + chr(msg[i] >> 8 & 0xff) + chr(
                msg[i] >> 16 & 0xff) + chr(msg[i] >> 24 & 0xff)
        )
    if key:
        return "".join(res)[0:ll]
    return "".join(res)

def get_xencode(msg, key):
    if msg == "":
        return ""
    pwd = sencode(msg, True)
    pwdk = sencode(key, False)
    if len(pwdk) < 4:
        pwdk = pwdk + [0] * (4 - len(pwdk))
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    q = math.floor(6 + 52 / (n + 1))
    d = 0
    while 0 < q:
        d = d + c & (0x8CE0D9BF | 0x731F2640)
        e = d >> 2 & 3
        p = 0
        while p < n:
            y = pwd[p + 1]
            m = z >> 5 ^ y << 2
            m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = pwd[p] + m & (0xEFB8D130 | 0x10472ECF)
            z = pwd[p]
            p = p + 1
        y = pwd[0]
        m = z >> 5 ^ y << 2
        m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[n] = pwd[n] + m & (0xBB390742 | 0x44C6F8BD)
        z = pwd[n]
        q = q - 1
    return lencode(pwd, False)

def is_online():
    """检测当前网络是否已在线认证"""
    try:
        ts = str(int(time.time() * 1000))
        data = parse_json(get(f"{SERVER}/cgi-bin/rad_user_info?callback=cb&_={ts}", timeout=4))
        if data.get("error") == "ok":
            return True, data.get("online_ip", ""), data.get("user_name", "")
    except Exception:
        pass
    return False, "", ""

def login():
    """执行深澜 Srun Portal 认证"""
    if USERNAME == "YOUR_USERNAME" or not USERNAME:
        log("[!] 请先在 WebUI 或脚本中配置有效的学号与密码！")
        return False

    ts = str(int(time.time() * 1000))
    cb = f"jQuery1124_{ts}"

    # 1. 请求 challenge 获取动态 token 和 client_ip
    try:
        url = f"{SERVER}/cgi-bin/get_challenge?callback={cb}&username={USERNAME}&ip=&_={ts}"
        data = parse_json(get(url, timeout=5))
    except Exception as e:
        log(f"[!] 获取 challenge 网络错误: {e}")
        return False

    token = data.get("challenge", "")
    ip = data.get("client_ip", "")
    if not token:
        log(f"[!] 获取 challenge 失败: {data}")
        return False

    # 2. 构造加密参数
    n = "200"
    type_val = "1"
    info_dict = {
        "username": USERNAME,
        "password": PASSWORD,
        "ip": ip,
        "acid": AC_ID,
        "enc_ver": "srun_bx1"
    }
    info_raw = json.dumps(info_dict, separators=(',', ':'))
    info_encoded = "{SRBX1}" + get_base64(get_xencode(info_raw, token))

    # HMAC-MD5: key=token, message=PASSWORD
    hmd5 = hmac.new(token.encode('utf-8'), PASSWORD.encode('utf-8'), hashlib.md5).hexdigest()

    # SHA1 校验和串（严格对应 Srun 协议）
    chkstr = (
        token + USERNAME +
        token + hmd5 +
        token + AC_ID +
        token + ip +
        token + n +
        token + type_val +
        token + info_encoded
    )
    chksum = hashlib.sha1(chkstr.encode('utf-8')).hexdigest()

    # 3. 提交登录请求
    params = urllib.parse.urlencode({
        "callback": cb,
        "action": "login",
        "username": USERNAME,
        "password": "{MD5}" + hmd5,
        "ac_id": AC_ID,
        "ip": ip,
        "chksum": chksum,
        "info": info_encoded,
        "n": n,
        "type": type_val,
        "os": "Windows 10",
        "name": "Windows",
        "double_stack": "0",
        "_": ts
    })

    try:
        resp = parse_json(get(f"{SERVER}/cgi-bin/srun_portal?{params}", timeout=6))
    except Exception as e:
        log(f"[!] 提交认证请求异常: {e}")
        return False

    if resp.get("error") == "ok" or resp.get("ecode") == "E0000":
        log(f"[+] 认证成功！IP: {ip}")
        return True
    else:
        err = resp.get("error_msg") or resp.get("error") or resp
        log(f"[-] 认证失败: {err}")
        return False

def logout():
    """注销当前设备的认证状态"""
    try:
        online, ip, user = is_online()
        if not online:
            log("[=] 当前未在线，无需注销")
            return True
        ts = str(int(time.time() * 1000))
        cb = f"jQuery1124_{ts}"
        params = urllib.parse.urlencode({
            "callback": cb,
            "action": "logout",
            "username": user or USERNAME,
            "ac_id": AC_ID,
            "ip": ip,
            "_": ts
        })
        resp = parse_json(get(f"{SERVER}/cgi-bin/srun_portal?{params}", timeout=5))
        if resp.get("error") == "ok" or resp.get("ecode") == 0:
            log(f"[+] 注销成功！IP: {ip}")
            return True
        else:
            log(f"[-] 注销响应: {resp}")
            return False
    except Exception as e:
        log(f"[!] 注销异常: {e}")
        return False

def run_once():
    online, ip, user = is_online()
    if online:
        log(f"[=] 当前在线正常（账号: {user}, IP: {ip}）")
        return True
    else:
        log("[*] 检测到未认证或已掉线，开始登录认证...")
        success = login()
        if not success:
            time.sleep(2)
            log("[*] 重试一次认证...")
            success = login()
        return success

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        online, ip, user = is_online()
        if online:
            print(f"ONLINE {user} {ip}")
            sys.exit(0)
        else:
            print("OFFLINE")
            sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--logout":
        ok = logout()
        sys.exit(0 if ok else 1)
    
    ok = run_once()
    sys.exit(0 if ok else 1)
