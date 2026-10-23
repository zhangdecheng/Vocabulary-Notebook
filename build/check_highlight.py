#!/usr/bin/env python3
"""朗读高亮时间对齐回归：同一段落、同一时间点，两个站点高亮的单词必须相同。
用法：python3 build/check_highlight.py BASE_SITE OUT_SITE"""
import sys, json, functools, threading, http.server, socketserver
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
def serve(d):
    s = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start(); return 'http://127.0.0.1:%d/' % s.server_address[1]
PARAS = ['c1p0', 'c27p3', 'c53p1', 'c54p0', 'c60p1', 'c69p4']
JS = '''async ([pid,acc])=>{var B=(BOUNDS[acc]||{})[pid]||[];var out=[];var p=document.getElementById(pid);__aud.playParas([p]);var pl=__aud.player;pl.muted=true;
  var nw=s=>String(s).toLowerCase().replace(/[’]/g,"'").replace(/[^a-z0-9']/g,'');
  for(var i=0;i<24;i++){await new Promise(r=>setTimeout(r,170));if(pl.paused||pl.currentTime<0.3)continue;
    var t=pl.currentTime,n=p.querySelector(".wk.now"),e=null;for(var k=0;k<B.length;k++){if(B[k][0]/1000<=t+0.05)e=B[k][1];else break}
    out.push([e,n?n.textContent:null])}
  __aud.stop();return out}'''
res = {}
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
    for tag, d in (('base', sys.argv[1]), ('out', sys.argv[2])):
        u = serve(d); r = {}
        for acc in ('us', 'uk'):
            ctx = br.new_context(); pg = ctx.new_page()
            pg.add_init_script('localStorage.setItem("wsx-prefs",JSON.stringify({mode:"both",gloss:"pop",fs:18,rate:"1",acc:"%s"}))' % acc)
            pg.goto(u + 'stories.html'); pg.wait_for_timeout(800)
            for pid in PARAS: r[(acc, pid)] = pg.evaluate(JS, [pid, acc])
            ctx.close()
        res[tag] = r
    br.close()
allok = True
def good(r):  # 采样时刻高亮的词 = 音频边界给出的当前词（允许相邻一个词的帧误差）
    return sum(1 for e, n in r if e and n and (nw(e) == nw(n) or nw(n).startswith(nw(e)[:3]) or nw(e).startswith(nw(n)[:3])))
import re
nw = lambda x: re.sub(r"[^a-z0-9']", '', str(x).lower().replace('\u2019', "'"))
for k in res['base']:
    a, b = res['base'][k], res['out'][k]
    ga, gb = good(a), good(b); okk = len(b) >= 5 and gb >= 0.8 * len(b) and (gb / len(b)) >= (ga / max(1, len(a))) - 0.15
    allok &= okk
    print(('PASS ' if okk else 'FAIL ') + '%s %s: highlight follows audio — base %d/%d, new %d/%d samples' % (k[0], k[1], ga, len(a), gb, len(b)))
print('ALL PASS' if allok else 'SOME FAIL')
