#!/usr/bin/env python3
"""PR #2 前后对比截图（手机 390×844 日间）：第 60 章结尾、页面最后（第 69 章后）。用法：python3 build/shots_pr2.py BEFORE_SITE AFTER_SITE OUT_DIR"""
import sys, os, functools, threading, http.server, socketserver
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
def serve(d):
    s = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start(); return 'http://127.0.0.1:%d/stories.html' % s.server_address[1]
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49'
os.makedirs(sys.argv[3], exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    for tag, d in (('before', sys.argv[1]), ('after', sys.argv[2])):
        u = serve(d)
        for th in ('light', 'dark'):
            ctx = b.new_context(viewport={'width': 390, 'height': 844}, user_agent=UA, is_mobile=True, has_touch=True, device_scale_factor=2); pg = ctx.new_page()
            pg.add_init_script('localStorage.setItem("wsv2-theme","%s")' % th)
            pg.goto(u); pg.wait_for_timeout(1000)
            # 第 60 章：收起词表，看章末
            pg.evaluate('document.querySelector("#c60 details.wl").open=false;var r=document.querySelector("#c60 details.wl").getBoundingClientRect();window.scrollTo({top:scrollY+r.top-260,behavior:"instant"})'); pg.wait_for_timeout(600)
            pg.screenshot(path=os.path.join(sys.argv[3], '%s_c60_end_%s.png' % (tag, th)))
            pg.evaluate('document.querySelector("#c69 details.wl").open=false;var r=document.querySelector("#c69 details.wl").getBoundingClientRect();window.scrollTo({top:scrollY+r.top-260,behavior:"instant"})'); pg.wait_for_timeout(600)
            pg.screenshot(path=os.path.join(sys.argv[3], '%s_c69_page_end_%s.png' % (tag, th)))
            ctx.close()
    b.close()
print('ok')
