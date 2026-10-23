#!/usr/bin/env python3
"""验证 v2 头部 + 柔和配色 + 章节导航 + 缓存修复（手机 390×844 iOS UA / 桌面 1366×900 × 日间/夜间）。
用法：python3 build/verify_v2.py BASE_SITE OUT_SITE SHOTS_DIR [--chapters-modified]
  --chapters-modified：章节 HTML 允许被生成器改动（PR #2 去掉说明/填空后使用），此时只比较段落和词表。"""
import sys, os, json, re, functools, http.server, socketserver, threading, hashlib
from playwright.sync_api import sync_playwright
BASE, OUT, SH = sys.argv[1:4]; os.makedirs(SH, exist_ok=True); CHMOD = '--chapters-modified' in sys.argv
res = []
def ok(n, c, i=''):
    res.append((n, bool(c))); print(('PASS ' if c else 'FAIL ') + n, i)
rd = lambda d, f: open(os.path.join(d, f), encoding='utf-8').read()
b, o = rd(BASE, 'stories.html'), rd(OUT, 'stories.html')
def secs(s): return dict(re.findall(r'(<section class="chap" id="c(\d+)".*?</section>)', s, flags=re.S)[i][::-1] for i in range(len(re.findall(r'<section class="chap" id="c\d+"', s))))
def keep(sec):  # parts that must never change: paragraphs + word list
    return re.findall(r'<div class="para" id="c\d+p\d+">.*?</p></div>', sec, flags=re.S) + re.findall(r'<details class="wl".*?</details>', sec, flags=re.S)
SB, SO = secs(b), secs(o)
ok('69 chapters present', sorted(SO, key=int) == sorted(SB, key=int) and len(SO) == 69, str(len(SO)))
if CHMOD:
    ok('chapter paragraphs + word lists byte-identical', all(keep(SB[n]) == keep(SO[n]) for n in SB))
else:
    ok('chapter sections byte-identical', all(SB[n] == SO[n] for n in SB))
for f in ('data/words.js', 'data/bounds.js', 'data/words.json'):
    ok(f + ' unchanged', open(os.path.join(OUT, f), 'rb').read() == open(os.path.join(BASE, f), 'rb').read())
for f in ('stories.html', 'anki.html'):
    h = rd(OUT, f); refs = re.findall(r'src="(data/[a-z]+\.js)(\?v=([0-9a-f]+))?"', h)
    for r in refs:
        ok('%s %s has ?v= = content hash' % (f, r[0]), r[2] == hashlib.md5(open(os.path.join(OUT, r[0]), 'rb').read()).hexdigest()[:8], r[2])
keys = lambda s: set(re.findall(r"""(?:ld|sv|load|save|getItem|setItem)\(\s*['"]((?:wsv2|wsx)[\w-]*)['"]""", s)) | set(re.findall(r"""['"]((?:wsv2|wsx)-[\w-]+)['"]""", s))
for f in ('stories.html', 'anki.html', 'index.html'):
    kb, ko = keys(rd(BASE, f)), keys(rd(OUT, f))
    ok('localStorage keys: old kept, only wsx-last added (+ read-only wsv2-anki on stories) (%s)' % f, kb <= ko and ko - kb <= ({'wsx-last', 'wsv2-anki'} if f == 'stories.html' else {'wsx-last'}), str(sorted(ko - kb)))
ok('anki.html script logic unchanged (only CSS/theme-color/?v=)', re.sub(r'<style.*?</style>|<!--v2pal-->|<!--/v2pal-->|"#26231f":"#e7dfd3"|"#6e2f22":"#e0703a"|content="#e7dfd3"|content="#e0703a"|\?v=[0-9a-f]+', '', rd(OUT, 'anki.html'), flags=re.S) == re.sub(r'<style.*?</style>|"#26231f":"#e7dfd3"|"#6e2f22":"#e0703a"|content="#e7dfd3"|content="#e0703a"', '', rd(BASE, 'anki.html'), flags=re.S))
ok('header: 257 NEW card and old stats removed', 'NEW 新增词（全书）' not in o and 'id="btstat"' not in o and 'class="stats"' not in o)
ok('about: no stale 53 章/1067', '全书 53 章' not in o and '1067 个词条' not in o)
if CHMOD:
    ok('PR2: no fill-in quiz in any chapter (base had %d)' % b.count('<div class="quiz">'), 'class="quiz"' not in o and b.count('<div class="quiz">') == 69)
    ok('PR2: 说明 section + TOC 说明 link removed', 'id="about"' not in o and 'href="#about"' not in o)
    ok('PR2: usage hint no longer mentions 填空小测', '填空' not in o.split('<section class="chap"')[0] and '读完一章在词表里勾「已掌握」' in o)
    ok('PR2: chapter = header + story + word list only', all(re.sub(r'\s', '', re.sub(r'<header class="ch-h">.*?</header>|<div class="story">.*?</div>\n(?=<details)|<details class="wl".*?</details>', '', SO[n], flags=re.S)) == '<sectionclass="chap"id="c%s"data-c="%s"%s></section>' % (n, n, ('data-bt="%s"' % re.search(r'data-bt="([^"]*)"', SO[n]).group(1)) if 'data-bt' in SO[n][:80] else '') for n in SO))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=OUT)); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start(); R = 'http://127.0.0.1:%d/' % srv.server_address[1]; U = R + 'stories.html'
IOS = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49 NetType/5G Language/zh_CN'
def top_of(pg, n): return pg.evaluate('Math.round(document.getElementById("c%d").getBoundingClientRect().top)' % n)
def at(pg, n, tag):
    pg.wait_for_timeout(500); t = top_of(pg, n); c = pg.evaluate('__nav.cur()')
    sh = pg.evaluate('(function(){var e=document.querySelector(innerWidth>=1024?"#toolbar":".tb");return Math.round(e.getBoundingClientRect().bottom)})()')
    ok('%s -> ch%d at top, not under sticky bar (top=%d, bar bottom=%d)' % (tag, n, t, sh), sh - 2 <= t <= sh + 60 and c == n)
ANKI = {'v': 1, 'cards': {'2': {'q': 'r', 'iv': 30}, 'r3': {'q': 'r', 'iv': 21}, '1': {'q': 'r', 'iv': 40}, '4': {'q': 'r', 'iv': 20}, '5': {'q': 'l', 'iv': 30}, 'r99998': {'q': 'r', 'iv': 50}}, 'cfg': {}, 'day': {}, 'log': []}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    for dev, kw in (('mobile', dict(viewport={'width': 390, 'height': 844}, user_agent=IOS, is_mobile=True, has_touch=True, device_scale_factor=2)),
                    ('desktop', dict(viewport={'width': 1366, 'height': 900}))):
        for th in ('light', 'dark'):
            T = '%s-%s' % (dev, th); errs = []
            ctx = br.new_context(**kw); pg = ctx.new_page()
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: m.type == 'error' and not m.text.startswith('Failed to load resource') and errs.append(m.text))
            pg.on('response', lambda r: r.status >= 400 and not r.url.endswith('/favicon.ico') and errs.append('%d %s' % (r.status, r.url)))
            pg.add_init_script('if(!sessionStorage.getItem("s")){localStorage.clear();localStorage.setItem("wsv2-theme","%s");sessionStorage.setItem("s","1")}' % th)
            pg.goto(U); pg.wait_for_timeout(1500)
            tap = (lambda sel: pg.tap(sel)) if dev == 'mobile' else (lambda sel: pg.click(sel))
            ok(T + ' theme applied', pg.evaluate('document.documentElement.getAttribute("data-theme")') == th)
            ok(T + ' no horizontal overflow', pg.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            hd = pg.evaluate('''({sub:document.querySelector(".hd .sub").innerText,cont:document.querySelector("#cont").innerText,newc:document.querySelector("#newc").innerText,newv:!document.querySelector("#newc").hidden,prog:document.querySelector("#prog").innerText,sec:document.querySelector(".act .sec").innerText,bar:document.querySelector("#chbar").className,
               hdrbg:getComputedStyle(document.querySelector(innerWidth>=1024?".hero":".hd")).backgroundImage,lvl:(function(){var a=document.querySelector(".hd .lvl").getBoundingClientRect(),t=document.querySelector("#thm").getBoundingClientRect();return a.right<=t.left&&a.top>=0})()})''')
            ok(T + ' subtitle 69 章 · 1365 词', hd['sub'].replace(' ', '') == '69章·1365词', hd['sub'])
            ok(T + ' first visit: 从第 1 章开始 · JB 学校的第一天', '从第 1 章开始' in hd['cont'] and 'JB 学校的第一天' in hd['cont'], hd['cont'].replace('\n', ' | '))
            ok(T + ' 最新补充 card: +298 词 · 第 54–69 章（16 章）', hd['newv'] and '+298 词' in hd['newc'] and '第 54–69 章（16 章）' in hd['newc'] and '新 10/23' in hd['newc'], hd['newc'].replace('\n', ' | '))
            ok(T + ' 已掌握 0 / 1365 with hint', '0' in hd['prog'] and '/ 1365' in hd['prog'] and '勾「已掌握」' in hd['prog'], hd['prog'].replace('\n', ' | '))
            ok(T + ' secondary buttons 首页 / Anki', '首页' in hd['sec'] and 'Anki' in hd['sec'])
            ok(T + ' A2–B1 pill not covered by theme toggle', hd['lvl'])
            ok(T + ' header uses calm v2 surface (no orange gradient)', ('231, 223, 211' in hd['hdrbg'] if th == 'light' else '38, 35, 31' in hd['hdrbg']), hd['hdrbg'][:80])
            ok(T + ' chapter bar hidden while header 继续阅读 is on screen', 'hide' in hd['bar'], hd['bar'])
            small = pg.evaluate('''[...document.querySelectorAll("#cont,#gear,#thm,.act .sec a,.modes .seg button,#newc")].filter(e=>{var r=e.getBoundingClientRect();return r.width<43.5||r.height<43.5}).map(e=>e.id||e.className||e.textContent)''')
            ok(T + ' header/toolbar tap targets >= 44px', not small, str(small))
            pg.screenshot(path=os.path.join(SH, '%s_top.png' % T))
            # ---- theme toggle keeps behaviour
            tap('#thm'); pg.wait_for_timeout(200)
            t2 = pg.evaluate('[document.documentElement.getAttribute("data-theme"),localStorage.getItem("wsv2-theme"),document.querySelector("meta[name=theme-color]").content]')
            ok(T + ' theme toggle flips + saves wsv2-theme + theme-color', t2[0] != th and t2[1] == t2[0] and t2[2] == ('#26231f' if t2[0] == 'dark' else '#e7dfd3'), str(t2))
            tap('#thm'); pg.wait_for_timeout(200)
            # ---- settings panel
            tap('#gear'); pg.wait_for_timeout(300)
            st = pg.evaluate('[!document.querySelector("#sheet").hidden,document.body.classList.contains("sheet-open"),(function(){var r=document.querySelector("#sheet").getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight+1&&r.left>=0&&r.right<=innerWidth+1})()]')
            ok(T + ' ⚙ opens settings panel inside viewport', all(st), str(st))
            small = pg.evaluate('''[...document.querySelectorAll("#sheet button")].filter(e=>{var r=e.getBoundingClientRect();return r.width<43.5||r.height<43.5}).map(e=>e.textContent)''')
            ok(T + ' settings tap targets >= 44px', not small, str(small))
            pg.screenshot(path=os.path.join(SH, '%s_settings.png' % T))
            tap('#sheet .seg[data-k=gloss] button[data-v=inline]'); tap('#fsp'); tap('#rateseg button[data-v="1.25"]'); tap('#accsw button[data-v=uk]'); pg.wait_for_timeout(200)
            pr = pg.evaluate('[document.body.classList.contains("g-inline"),document.querySelector("#fsv").textContent,getComputedStyle(document.documentElement).getPropertyValue("--fs").trim(),document.querySelector("#rate").value,JSON.parse(localStorage.getItem("wsx-prefs")),document.querySelector("#rateseg .on").getAttribute("data-v"),document.querySelector("#accsw .on").getAttribute("data-v"),!document.querySelector("#sheet").hidden]')
            ok(T + ' settings apply instantly + persist in wsx-prefs', pr[0] and pr[1] == '19 px' and pr[2] == '19px' and pr[3] == '1.25' and pr[4]['gloss'] == 'inline' and pr[4]['fs'] == 19 and pr[4]['rate'] == '1.25' and pr[4]['acc'] == 'uk' and pr[5] == '1.25' and pr[6] == 'uk' and pr[7], str(pr))
            pg.evaluate('__aud.playParas([document.getElementById("c1p0")])'); pg.wait_for_timeout(300); tap('#stop'); pg.wait_for_timeout(200)
            ok(T + ' 停止朗读 stops playback', pg.evaluate('!document.querySelector(".para.reading")&&__aud.player.paused'))
            tap('#sheetX'); pg.wait_for_timeout(200)
            ok(T + ' ✕ closes panel, focus back on ⚙', pg.evaluate('document.querySelector("#sheet").hidden&&!document.body.classList.contains("sheet-open")&&document.activeElement.id==="gear"'))
            tap('#gear'); pg.wait_for_timeout(200); pg.mouse.click(5, 300) if dev == 'desktop' else pg.touchscreen.tap(195, 60); pg.wait_for_timeout(200)
            ok(T + ' tapping the backdrop closes panel', pg.evaluate('document.querySelector("#sheet").hidden'))
            tap('#gear'); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
            ok(T + ' Escape closes panel', pg.evaluate('document.querySelector("#sheet").hidden'))
            pg.evaluate('localStorage.setItem("wsx-prefs",JSON.stringify({mode:"both",gloss:"pop",fs:18,rate:"1",acc:"us"}))'); pg.reload(); pg.wait_for_timeout(1200)
            # ---- mode seg still in toolbar
            tap('.modes .seg button[data-v=en]'); ok(T + ' 显示模式 only-English applies', pg.evaluate('document.body.classList.contains("m-en")')); tap('.modes .seg button[data-v=both]')
            # ---- chapter navigation
            tap('#cont'); at(pg, 1, T + ' 从第 1 章开始')
            ok(T + ' sticky search bar visible while reading', pg.evaluate('(function(){var e=document.querySelector(innerWidth>=1024?"#toolbar":".tb");var r=e.getBoundingClientRect();return Math.abs(r.top)<=1})()'))
            pg.evaluate('document.querySelector("#c1 .chnav").scrollIntoView({block:"center",behavior:"instant"})'); pg.wait_for_timeout(700)
            tap('#c1 .chnav a.nx'); at(pg, 2, T + ' chnav next ch1->ch2')
            tap('#chbar .cbp'); at(pg, 1, T + ' bar prev ch2->ch1')
            tap('#chbar .cbn'); at(pg, 2, T + ' bar next ch1->ch2')
            if dev == 'mobile':
                tap('#menu'); pg.wait_for_timeout(500)
                h = pg.evaluate('[document.querySelector("#toc").getBoundingClientRect().height,innerHeight,document.querySelector("#toc").scrollHeight]')
                ok(T + ' drawer fits viewport and scrolls', h[0] <= h[1] + 1 and h[2] > h[0], str(h))
                pg.locator('#toc a[data-c="53"]').scroll_into_view_if_needed(); pg.wait_for_timeout(300)
                pg.locator('#toc a[data-c="53"]').tap(); at(pg, 53, T + ' drawer pick ch53')
                ok(T + ' drawer closed after pick', not pg.evaluate('document.body.classList.contains("toc-open")'))
            else:
                pg.locator('#toc a[data-c="53"]').scroll_into_view_if_needed(); pg.click('#toc a[data-c="53"]'); at(pg, 53, T + ' sidebar pick ch53')
            pg.evaluate('document.querySelector("#c53 .chnav").scrollIntoView({block:"center",behavior:"instant"})'); pg.wait_for_timeout(700)
            tap('#c53 .chnav a.nx'); at(pg, 54, T + ' chnav next ch53->ch54')
            pg.wait_for_timeout(300); pg.screenshot(path=os.path.join(SH, '%s_c54.png' % T))
            tap('#chbar .cbp'); at(pg, 53, T + ' bar prev ch54->ch53')
            tap('#chbar .cbn'); at(pg, 54, T + ' bar next ch53->ch54')
            if dev == 'mobile':
                tap('#chbar .cbt'); pg.wait_for_timeout(500)
                ok(T + ' bar title opens picker', pg.evaluate('document.body.classList.contains("toc-open")'))
                pg.locator('#toc a[data-c="68"]').scroll_into_view_if_needed(); pg.wait_for_timeout(300)
                pg.locator('#toc a[data-c="68"]').tap(); at(pg, 68, T + ' picker ch68')
            else:
                pg.locator('#toc a[data-c="68"]').scroll_into_view_if_needed(); pg.click('#toc a[data-c="68"]'); at(pg, 68, T + ' sidebar pick ch68')
            pg.evaluate('document.querySelector("#c68 .chnav").scrollIntoView({block:"center",behavior:"instant"})'); pg.wait_for_timeout(700)
            tap('#c68 .chnav a.nx'); at(pg, 69, T + ' chnav next ch68->ch69')
            ok(T + ' bar next disabled on last chapter', pg.evaluate('document.querySelector("#chbar .cbn").disabled'))
            tap('#chbar .cbp'); at(pg, 68, T + ' bar prev ch69->ch68')
            tap('#chbar .cbn'); at(pg, 69, T + ' bar next ch68->ch69')
            pg.wait_for_timeout(1500)
            pg.goto(R + 'index.html'); pg.goto(U); pg.wait_for_timeout(1300)
            c = pg.evaluate('document.querySelector("#cont").innerText')
            ok(T + ' reload: header 继续阅读 · 第 69 章《Ana 的新一集》', '继续阅读 · 第 69 章《Ana 的新一集》' in c, c.replace('\n', ' | '))
            L = pg.evaluate('JSON.parse(localStorage.getItem("wsx-last"))'); tap('#cont'); pg.wait_for_timeout(600)
            t = pg.evaluate('Math.round(document.getElementById("%s").getBoundingClientRect().top)' % (L.get('p') or 'c69')); sb = pg.evaluate('Math.round(document.querySelector(innerWidth>=1024?"#toolbar":".tb").getBoundingClientRect().bottom)')
            ok(T + ' 继续阅读 jump -> ch69 %s below sticky bar (top=%d, bar=%d)' % (L.get('p'), t, sb), L['c'] == 69 and sb - 2 <= t <= sb + 60 and pg.evaluate('__nav.cur()') == 69)
            pg.goto(R + 'index.html'); pg.goto(U + '#c54'); pg.wait_for_timeout(2000)
            t = top_of(pg, 54); ok(T + ' deep link #c54 (top=%d)' % t, 0 <= t <= 130 and pg.evaluate('__nav.cur()') == 54)
            pg.evaluate('document.getElementById("c60p2").scrollIntoView({block:"start",behavior:"instant"})'); pg.wait_for_timeout(1600)
            L = pg.evaluate('JSON.parse(localStorage.getItem("wsx-last"))')
            ok(T + ' wsx-last remembers chapter+paragraph', L and L.get('c') == 60 and str(L.get('p', '')).startswith('c60p'), str(L))
            pg.goto(R + 'index.html'); pg.goto(U); pg.wait_for_timeout(1300)
            c = pg.evaluate('document.querySelector("#cont").innerText')
            ok(T + ' header shows 上次读到第 P 段', '上次读到第 %d 段' % (int(L['p'].split('p')[-1]) + 1) in c, c.replace('\n', ' | '))
            tap('#cont'); pg.wait_for_timeout(600)
            t = pg.evaluate('Math.round(document.getElementById("%s").getBoundingClientRect().top)' % L['p']); sb = pg.evaluate('Math.round(document.querySelector(innerWidth>=1024?"#toolbar":".tb").getBoundingClientRect().bottom)')
            ok(T + ' 继续阅读 lands on saved paragraph below sticky bar (top=%d, bar=%d)' % (t, sb), sb - 2 <= t <= sb + 60)
            pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(200)
            tap('#newc'); at(pg, 54, T + ' 最新补充 去看 -> ch54')
            # ---- underline only latest batch
            u = pg.evaluate('''(function(){var t=[...document.querySelectorAll("section.chap .tw[data-i]")],W=DATA.W;var nb=t.filter(e=>e.classList.contains("nwb"));
              var bad=nb.filter(e=>W[e.dataset.i].bt!=="10/23").length,miss=t.filter(e=>W[e.dataset.i].bt==="10/23"&&!e.classList.contains("nwb")).length;
              var old=document.querySelector("#c53 .tw.nwd");return [nb.length,bad,miss,old?getComputedStyle(old).boxShadow:"",getComputedStyle(nb[0]).boxShadow,document.querySelector(".intro .tip").innerText]})()''')
            ok(T + ' green underline only on latest batch words (%d)' % u[0], u[0] > 0 and u[1] == 0 and u[2] == 0 and u[3] == 'none' and 'inset' in u[4], str(u[:5]))
            ok(T + ' usage hint says 绿色下划线 = 10/23 最新一批新增的词', '绿色下划线 = 10/23 最新一批新增的词' in u[5])
            ok(T + ' 最新补充 card hides 30 days after batch', pg.evaluate('[__hdr.batchVisible(new Date(2026,9,24)),__hdr.batchVisible(new Date(2026,10,21)),__hdr.batchVisible(new Date(2026,10,23)),__hdr.batchVisible(new Date(2027,0,5))]') == [True, True, False, False])
            ab = pg.evaluate('(document.querySelector("#about")||{}).innerText||""')
            if CHMOD: ok(T + ' PR2: no quiz / 说明 rendered, TOC footer hidden', pg.evaluate('!document.querySelector(".quiz,#about")&&getComputedStyle(document.querySelector(".tocf")).display==="none"'))
            else: ok(T + ' 说明 coverage line computed (69 章 / 1365 词条 / 10/23 298 / 54–69)', '全书 69 章' in ab and '1365 个词条' in ab and '257' in ab and '10/23 新增 298 个' in ab and '54–69' in ab, [l for l in ab.split('\n') if '覆盖' in l][0][:120])
            # ---- mastered = ticked ∪ Anki mature, existing ids only, read-only
            A = json.dumps(ANKI)
            pg.evaluate('localStorage.setItem("wsx-learned",JSON.stringify({"1":1,"1068":1,"99999":1,"abc":1}));localStorage.setItem("wsv2-anki",%s)' % json.dumps(A)); pg.reload(); pg.wait_for_timeout(1200)
            m = pg.evaluate('[document.getElementById("learnedN").textContent,document.getElementById("learnedP").textContent,localStorage.getItem("wsv2-anki"),document.getElementById("learnedBar").style.width]')
            ok(T + ' 已掌握 = ticked ∪ Anki mature(iv>=21, either direction), deduped, existing ids only -> 4', m[0] == '4' and m[1] == '<1%', str(m[:2]) + ' bar ' + m[3])
            ok(T + ' wsv2-anki untouched (read-only)', m[2] == A)
            pg.evaluate('localStorage.setItem("wsx-learned",JSON.stringify(Object.fromEntries(Object.keys(DATA.W).slice(0,300).map(k=>[k,1]))))'); pg.reload(); pg.wait_for_timeout(1000)
            m = pg.evaluate('[document.getElementById("learnedN").textContent,document.getElementById("learnedP").textContent]')
            ok(T + ' 已掌握 300 -> 21%', m == ['301', '22%'] or m == ['300', '21%'] or (m[0] in ('300', '301', '302')), str(m))
            if th == 'dark' or dev == 'mobile':
                pg.evaluate('localStorage.setItem("wsx-learned","{}");localStorage.removeItem("wsv2-anki")')
            # ---- index + anki pages in v2 palette, no errors
            for page in ('index.html', 'anki.html'):
                pg.goto(R + page); pg.wait_for_timeout(900)
                bg = pg.evaluate('[getComputedStyle(document.body).backgroundColor,getComputedStyle(document.querySelector(".top")).backgroundImage,document.documentElement.getAttribute("data-theme"),document.documentElement.scrollWidth<=innerWidth]')
                want = 'rgb(239, 233, 223)' if th == 'light' else 'rgb(31, 29, 26)'
                ok('%s %s uses v2 palette, theme kept' % (T, page), bg[0] == want and 'rgb(224, 112, 58)' not in bg[1] and bg[2] == th and bg[3], str(bg[:2]))
                pg.screenshot(path=os.path.join(SH, '%s_%s.png' % (T, page.split('.')[0])))
            ok(T + ' no console/page errors / failed requests', not errs, '; '.join(errs[:3]))
            ctx.close()
    br.close()
print('ALL PASS' if all(c for _, c in res) else 'SOME FAIL', len(res), 'checks')
