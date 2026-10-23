#!/usr/bin/env python3
"""头部截图（对应 Iris 示意图帧）+ 基本检查。用法：python3 build/shots_header.py SITE SHOTS_DIR [tag]"""
import sys, os, json, functools, threading, http.server, socketserver
from playwright.sync_api import sync_playwright
SITE, OUT = sys.argv[1], sys.argv[2]; TAG = sys.argv[3] if len(sys.argv) > 3 else ''
os.makedirs(OUT, exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
h = functools.partial(Q, directory=SITE); srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), h); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start(); U = 'http://127.0.0.1:%d/' % srv.server_address[1]
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49'
FR = [('mobile_night', 'dark', False, 'm'), ('mobile_day', 'light', False, 'm'), ('settings_night', 'dark', True, 'm'), ('settings_day', 'light', True, 'm'), ('desktop_night', 'dark', False, 'd'), ('desktop_day', 'light', False, 'd')]
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    for name, th, sheet, dev in FR:
        kw = dict(viewport={'width': 390, 'height': 844}, user_agent=UA, is_mobile=True, has_touch=True, device_scale_factor=2) if dev == 'm' else dict(viewport={'width': 1280, 'height': 900})
        ctx = b.new_context(**kw); pg = ctx.new_page()
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and 'favicon' not in m.text and errs.append(m.text))
        pg.add_init_script('localStorage.setItem("wsv2-theme","%s");localStorage.setItem("wsx-last",JSON.stringify({c:54,p:"c54p2",t:1}));localStorage.setItem("wsx-learned",JSON.stringify({"1":1,"2":1,"3":1}));' % th)
        pg.goto(U + 'stories.html'); pg.wait_for_timeout(1200)
        if sheet: pg.click('#gear'); pg.wait_for_timeout(400)
        f = os.path.join(OUT, '%s%s.png' % (TAG, name)); pg.screenshot(path=f); print(f)
        ctx.close()
    b.close()
print('errors', errs)
