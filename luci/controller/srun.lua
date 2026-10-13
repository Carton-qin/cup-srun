module("luci.controller.srun", package.seeall)

function index()
    entry({"admin", "services", "srun"},
          firstchild(), _("校园网认证"), 60)
    entry({"admin", "services", "srun", "index"},
          template("srun/index"), _("认证管理"), 1)
    entry({"admin", "services", "srun", "save"},
          call("action_save"), nil).leaf = true
    entry({"admin", "services", "srun", "do_auth"},
          call("action_auth"), nil).leaf = true
    entry({"admin", "services", "srun", "do_logout"},
          call("action_logout"), nil).leaf = true
    entry({"admin", "services", "srun", "status"},
          call("action_status"), nil).leaf = true
    entry({"admin", "services", "srun", "log"},
          call("action_log"), nil).leaf = true
end

local function read_config()
    local f = io.open("/usr/local/bin/srun_auth.py", "r")
    if not f then return {username="", password="", server="https://login.cup.edu.cn"} end
    local content = f:read("*all"); f:close()
    local username = content:match('USERNAME%s*=%s*"([^"]*)"') or ""
    local password = content:match('PASSWORD%s*=%s*"([^"]*)"') or ""
    local server   = content:match('SERVER%s*=%s*"([^"]*)"')   or "https://login.cup.edu.cn"
    if username == "YOUR_USERNAME" then username = "" end
    if password == "YOUR_PASSWORD" then password = "" end
    return {username=username, password=password, server=server}
end

local function write_config(username, password)
    local f = io.open("/usr/local/bin/srun_auth.py", "r")
    if not f then return false end
    local content = f:read("*all"); f:close()
    local safe_user = username:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("%%", "%%%%")
    local safe_pass = password:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("%%", "%%%%")
    content = content:gsub('USERNAME%s*=%s*"[^"]*"', 'USERNAME = "' .. safe_user .. '"')
    content = content:gsub('PASSWORD%s*=%s*"[^"]*"', 'PASSWORD = "' .. safe_pass .. '"')
    local fw = io.open("/usr/local/bin/srun_auth.py", "w")
    if not fw then return false end
    fw:write(content); fw:close()
    return true
end

-- 解析当前 crontab 中的配置
local function get_cron_info()
    local f = io.open("/etc/crontabs/root", "r")
    local enabled = false
    local interval = 2
    if f then
        for line in f:lines() do
            if line:find("srun_auth%.py") then
                if not line:match("^%s*#") then
                    enabled = true
                    if line:match("^%* %* %* %* %*") then
                        interval = 1
                    elseif line:match("^0 %* %* %* %*") then
                        interval = 60
                    else
                        local h = line:match("^0 %*/(%d+) %* %* %*")
                        if h then
                            interval = (tonumber(h) or 1) * 60
                        else
                            local m = line:match("^%*/(%d+) %* %* %* %*")
                            if m then interval = tonumber(m) or 2 end
                        end
                    end
                end
            end
        end
        f:close()
    end
    return {enabled = enabled, interval = interval}
end

-- 生成并更新 crontab
local function update_cron(enabled, interval)
    interval = tonumber(interval) or 2
    if interval < 1 then interval = 1 end
    if interval > 1440 then interval = 1440 end

    local f = io.open("/etc/crontabs/root", "r")
    local lines = {}
    if f then
        for line in f:lines() do
            if not line:find("srun_auth%.py") then
                table.insert(lines, line)
            end
        end
        f:close()
    end

    if enabled then
        local spec = ""
        if interval == 1 then
            spec = "* * * * *"
        elseif interval < 60 then
            spec = "*/" .. interval .. " * * * *"
        elseif interval % 60 == 0 then
            local h = math.floor(interval / 60)
            spec = (h == 1) and "0 * * * *" or ("0 */" .. h .. " * * *")
        else
            local h = math.max(1, math.floor(interval / 60))
            spec = (h == 1) and "0 * * * *" or ("0 */" .. h .. " * * *")
        end
        table.insert(lines, spec .. " /usr/bin/python3 /usr/local/bin/srun_auth.py >/dev/null 2>&1")
    end

    local fw = io.open("/etc/crontabs/root", "w")
    if fw then
        fw:write(table.concat(lines, "\n") .. "\n")
        fw:close()
        luci.sys.exec("/etc/init.d/cron restart 2>/dev/null")
    end
end

function action_save()
    local http = require "luci.http"
    local username = http.formvalue("username") or ""
    local password = http.formvalue("password") or ""
    local cron_enable = (http.formvalue("cron_enable") == "1")
    local cron_interval = tonumber(http.formvalue("cron_interval")) or 2

    local ok1 = write_config(username, password)
    update_cron(cron_enable, cron_interval)

    local redirect_url = require("luci.dispatcher").build_url("admin", "services", "srun", "index")
    if ok1 then
        http.redirect(redirect_url .. "?msg=saved")
    else
        http.redirect(redirect_url .. "?msg=error")
    end
end

function action_auth()
    local http = require "luci.http"
    local result = luci.sys.exec("/usr/bin/python3 /usr/local/bin/srun_auth.py 2>&1")
    http.prepare_content("application/json")
    http.write('{"result":' .. luci.jsonc.stringify(result) .. '}')
end

function action_logout()
    local http = require "luci.http"
    local result = luci.sys.exec("/usr/bin/python3 /usr/local/bin/srun_auth.py --logout 2>&1")
    http.prepare_content("application/json")
    http.write('{"result":' .. luci.jsonc.stringify(result) .. '}')
end

function action_status()
    local http = require "luci.http"
    local py_check = [[
import json, re, urllib.request, ssl, time
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    ts = str(int(time.time()*1000))
    url = "https://login.cup.edu.cn/cgi-bin/rad_user_info?callback=x&_=" + ts
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    resp = urllib.request.urlopen(req, context=ctx, timeout=8).read().decode()
    m = re.search(r'\((.+)\)', resp)
    data = json.loads(m.group(1)) if m else {}
    if data.get("error") == "ok":
        print(json.dumps({"online":True,"username":data.get("user_name",""),"ip":data.get("online_ip","")}))
    else:
        print(json.dumps({"online":False}))
except Exception as e:
    print(json.dumps({"online":False,"err":str(e)}))
]]
    local result = luci.sys.exec("/usr/bin/python3 -c '" .. py_check:gsub("'", "'\\''") .. "' 2>/dev/null")
    http.prepare_content("application/json")
    http.write(result ~= "" and result or '{"online":false}')
end

function action_log()
    local http = require "luci.http"
    local f = io.open("/var/log/srun_auth.log", "r")
    local lines = {}
    if f then
        for line in f:lines() do
            table.insert(lines, line)
        end
        f:close()
    end
    local start = math.max(1, #lines - 59)
    local out = {}
    for i = start, #lines do table.insert(out, lines[i]) end
    http.prepare_content("text/plain; charset=utf-8")
    http.write(table.concat(out, "\n"))
end
