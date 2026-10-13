#!/usr/bin/env python3
"""
中国石油大学（北京）校园网认证 - Web 管理服务
运行端口: 8880
访问地址: http://<路由器IP>:8880
"""

import hashlib, hmac as hmac_lib, json, re, time, math
import urllib.request, urllib.parse, ssl, os, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import html as html_mod

CONFIG_FILE = '/usr/local/bin/srun_auth.py'
LOG_FILE    = '/var/log/srun_auth.log'
PORT        = 8880
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ─── 读写配置 ───────────────────────────────────────────────
def read_config():
    try:
        with open(CONFIG_FILE) as f:
            content = f.read()
        username = re.search(r'USERNAME\s*=\s*"([^"]*)"', content)
        password = re.search(r'PASSWORD\s*=\s*"([^"]*)"', content)
        server   = re.search(r'SERVER\s*=\s*"([^"]*)"', content)
        ac_id    = re.search(r'AC_ID\s*=\s*"([^"]*)"', content)
        u = username.group(1) if username else ''
        p = password.group(1) if password else ''
        if u == 'YOUR_USERNAME': u = ''
        if p == 'YOUR_PASSWORD': p = ''
        return {
            'username': u,
            'password': p,
            'server':   server.group(1)   if server   else 'https://login.cup.edu.cn',
            'ac_id':    ac_id.group(1)    if ac_id    else '1',
        }
    except:
        return {'username':'','password':'','server':'https://login.cup.edu.cn','ac_id':'1'}

def write_config(username, password):
    with open(CONFIG_FILE) as f:
        content = f.read()
    content = re.sub(r'USERNAME\s*=\s*"[^"]*"', f'USERNAME = "{username}"', content)
    content = re.sub(r'PASSWORD\s*=\s*"[^"]*"', f'PASSWORD = "{password}"', content)
    with open(CONFIG_FILE, 'w') as f:
        f.write(content)

# ─── 网络状态检测 ────────────────────────────────────────────
def check_status():
    try:
        cfg = read_config()
        server = cfg['server']
        ts = str(int(time.time() * 1000))
        url = f"{server}/cgi-bin/rad_user_info?callback=jQuery_{ts}&_={ts}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        resp = urllib.request.urlopen(req, context=CTX, timeout=8).read().decode()
        m = re.search(r'\((.+)\)', resp)
        if m:
            data = json.loads(m.group(1))
            if data.get('error') == 'ok':
                return {'online': True, 'username': data.get('user_name',''), 'ip': data.get('online_ip','')}
    except:
        pass
    return {'online': False}

def run_auth():
    result = subprocess.run(['python3', CONFIG_FILE], capture_output=True, text=True, timeout=20)
    return (result.stdout + result.stderr).strip()

def run_logout():
    result = subprocess.run(['python3', CONFIG_FILE, '--logout'], capture_output=True, text=True, timeout=15)
    return (result.stdout + result.stderr).strip()

def read_log(lines=50):
    try:
        with open(LOG_FILE) as f:
            all_lines = f.readlines()
        return ''.join(all_lines[-lines:])
    except:
        return '（暂无日志）'

# ─── HTML 模板 ───────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>校园网认证管理</title>
<style>
  :root {
    --blue: #2563eb; --blue-light: #eff6ff; --green: #16a34a; --green-light: #f0fdf4;
    --red: #dc2626; --red-light: #fef2f2; --gray: #6b7280; --border: #e5e7eb;
    --bg: #f9fafb; --card: #ffffff; --text: #111827;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); min-height: 100vh; }
  .header { background: var(--blue); color: white; padding: 16px 24px;
            display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.15); }
  .header h1 { font-size: 18px; font-weight: 600; }
  .header .sub { font-size: 13px; opacity: .8; margin-top: 2px; }
  .container { max-width: 860px; margin: 24px auto; padding: 0 16px; display: grid; gap: 20px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
  .card-header { padding: 16px 20px; border-bottom: 1px solid var(--border);
                 font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 8px; }
  .card-body { padding: 20px; }
  .status-badge { display: inline-flex; align-items: center; gap: 6px;
                  padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 500; }
  .status-badge.online  { background: var(--green-light); color: var(--green); }
  .status-badge.offline { background: var(--red-light);   color: var(--red);   }
  .status-badge::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
  .info-item { background: var(--bg); border-radius: 8px; padding: 12px 16px; }
  .info-item .label { font-size: 12px; color: var(--gray); margin-bottom: 4px; }
  .info-item .value { font-size: 15px; font-weight: 500; font-family: monospace; }
  .form-group { margin-bottom: 16px; }
  .form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: var(--gray); }
  .form-group input { width: 100%; padding: 10px 14px; border: 1px solid var(--border);
                      border-radius: 8px; font-size: 14px; outline: none; transition: border .2s; }
  .form-group input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
  .btn { padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; font-weight: 500;
         cursor: pointer; transition: .2s; display: inline-flex; align-items: center; gap: 6px; }
  .btn-primary { background: var(--blue); color: white; }
  .btn-primary:hover { background: #1d4ed8; }
  .btn-success { background: var(--green); color: white; }
  .btn-success:hover { background: #15803d; }
  .btn-danger { background: var(--red); color: white; }
  .btn-danger:hover { background: #b91c1c; }
  .btn-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
  .log-box { background: #0f172a; color: #94a3b8; font-family: monospace; font-size: 13px;
             padding: 16px; border-radius: 8px; max-height: 300px; overflow-y: auto;
             white-space: pre-wrap; word-break: break-all; line-height: 1.6; }
  .log-box .ok   { color: #86efac; }
  .log-box .err  { color: #fca5a5; }
  .alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 16px; }
  .alert-success { background: var(--green-light); color: var(--green); border: 1px solid #bbf7d0; }
  .alert-error   { background: var(--red-light);   color: var(--red);   border: 1px solid #fecaca; }
  .refresh-note { font-size: 12px; color: var(--gray); margin-top: 8px; }
  @media(max-width:600px) { .info-grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="header">
  <div>🌐</div>
  <div>
    <div class="h1">校园网认证管理</div>
    <div class="sub">中国石油大学（北京）· iStoreOS / OpenWrt</div>
  </div>
</div>
<div class="container">

  <!-- 状态卡片 -->
  <div class="card">
    <div class="card-header">📡 当前状态
      <a href="/" style="margin-left:auto;font-size:12px;color:var(--gray);text-decoration:none">🔄 刷新</a>
    </div>
    <div class="card-body">
      {STATUS_HTML}
    </div>
  </div>

  <!-- 手动认证 -->
  <div class="card">
    <div class="card-header">⚡ 手动操作</div>
    <div class="card-body">
      {AUTH_MSG}
      <div class="btn-row">
        <form method="POST" action="/auth" style="display:inline">
          <button class="btn btn-success" type="submit">🔑 立即认证</button>
        </form>
        <form method="POST" action="/logout" style="display:inline" onsubmit="return confirm('确定要注销下线当前校园网连接吗？')">
          <button class="btn btn-danger" type="submit">🚪 注销下线</button>
        </form>
      </div>
      <p class="refresh-note">后台保活：系统后台定时自动检测，掉线自动重连</p>
    </div>
  </div>

  <!-- 配置修改 -->
  <div class="card">
    <div class="card-header">⚙️ 账号配置</div>
    <div class="card-body">
      {SAVE_MSG}
      <form method="POST" action="/save">
        <div class="form-group">
          <label>学号 / 用户名</label>
          <input type="text" name="username" value="{USERNAME}" placeholder="请输入学号" autocomplete="off" required>
        </div>
        <div class="form-group">
          <label>校园网密码</label>
          <input type="password" name="password" value="{PASSWORD}" placeholder="请输入密码" required>
        </div>
        <div class="form-group">
          <label>认证服务器</label>
          <input type="text" name="server" value="{SERVER}" readonly style="background:#f3f4f6;color:var(--gray)">
        </div>
        <div class="btn-row">
          <button class="btn btn-primary" type="submit">💾 保存配置</button>
        </div>
      </form>
    </div>
  </div>

  <!-- 日志 -->
  <div class="card">
    <div class="card-header">📋 认证日志</div>
    <div class="card-body">
      <div class="log-box">{LOG}</div>
    </div>
  </div>

</div>
<script>
  // 30秒自动刷新状态
  setTimeout(() => location.reload(), 30000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass  # 静默请求日志

    def send_page(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def redirect(self, path):
        self.send_response(302)
        self.send_header('Location', path)
        self.end_headers()

    def render(self, save_msg='', auth_msg=''):
        st  = check_status()
        cfg = read_config()
        log = html_mod.escape(read_log())

        if st['online']:
            status_html = f"""
            <span class="status-badge online">已认证在线</span>
            <div class="info-grid">
              <div class="info-item"><div class="label">登录账号</div><div class="value">{st.get('username','—')}</div></div>
              <div class="info-item"><div class="label">IP 地址</div><div class="value">{st.get('ip','—')}</div></div>
            </div>"""
        else:
            status_html = '<span class="status-badge offline">未认证 / 离线</span>'

        page = HTML.replace('{STATUS_HTML}', status_html)
        page = page.replace('{USERNAME}', html_mod.escape(cfg['username']))
        page = page.replace('{PASSWORD}', html_mod.escape(cfg['password']))
        page = page.replace('{SERVER}',   html_mod.escape(cfg['server']))
        page = page.replace('{LOG}',      log)
        page = page.replace('{SAVE_MSG}', save_msg)
        page = page.replace('{AUTH_MSG}', auth_msg)
        return page

    def do_GET(self):
        if self.path == '/':
            self.send_page(self.render())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length).decode('utf-8')
        params = urllib.parse.parse_qs(body)

        if self.path == '/save':
            username = params.get('username', [''])[0].strip()
            password = params.get('password', [''])[0].strip()
            write_config(username, password)
            msg = '<div class="alert alert-success">✅ 配置已保存并即时生效！</div>'
            self.send_page(self.render(save_msg=msg))

        elif self.path == '/auth':
            result = run_auth()
            if '成功' in result or 'ok' in result.lower():
                msg = f'<div class="alert alert-success">✅ 认证成功！</div>'
            else:
                msg = f'<div class="alert alert-error">⚠️ {html_mod.escape(result)}</div>'
            self.send_page(self.render(auth_msg=msg))

        elif self.path == '/logout':
            result = run_logout()
            if '成功' in result or 'ok' in result.lower():
                msg = f'<div class="alert alert-success">✅ 已成功注销下线！</div>'
            else:
                msg = f'<div class="alert alert-error">⚠️ {html_mod.escape(result)}</div>'
            self.send_page(self.render(auth_msg=msg))

        else:
            self.redirect('/')

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'[+] Srun Web UI 已启动：http://0.0.0.0:{PORT}')
    server.serve_forever()
