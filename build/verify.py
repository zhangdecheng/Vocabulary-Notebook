#!/usr/bin/env python3
"""验证：旧卡片/旧章节/旧音频/存储键完全未变 + 无头 Chrome 截图（桌面/手机 × 日间/夜间）。
用法：python3 build/verify.py BASE_SITE OUT_SITE SHOTS_DIR [--chrome /usr/bin/google-chrome]"""
import json, os, re, sys, hashlib, threading, functools, http.server, socketserver
BASE, OUT, SHOTS = sys.argv[1:4]
CHROME = sys.argv[sys.argv.index('--chrome') + 1] if '--chrome' in sys.argv else '/usr/bin/google-chrome'
res = {}
def ok(name, cond, info=''):
    res[name] = {'pass': bool(cond), 'info': info}; print(('PASS ' if cond else 'FAIL ') + name, info)
B = json.load(open(os.path.join(BASE, 'data/words.json'), encoding='utf-8'))
N = json.load(open(os.path.join(OUT, 'data/words.json'), encoding='utf-8'))
old = sorted(B['W'], key=int)
ok('old W entries identical (deep equal, every field)', all(B['W'][k] == N['W'][k] for k in old), '%d entries' % len(old))
ok('old W canonical sha256 identical', hashlib.sha256(json.dumps([B['W'][k] for k in old], ensure_ascii=False, sort_keys=True).encode()).hexdigest() == hashlib.sha256(json.dumps([N['W'][k] for k in old], ensure_ascii=False, sort_keys=True).encode()).hexdigest())
ok('old CH/CT identical', all(B['CH'][k] == N['CH'][k] and B['CT'][k] == N['CT'][k] for k in B['CH']), '%d chapters' % len(B['CH']))
newids = sorted(set(N['W']) - set(B['W']), key=int)
ok('new ids do not collide and start after max old id', int(newids[0]) > int(old[-1]), '%s..%s (%d)' % (newids[0], newids[-1], len(newids)))
ok('old ids still present in same key order', list(N['W'].keys())[:len(old)] == list(B['W'].keys()))
# old chapter sections byte-identical
bs = open(os.path.join(BASE, 'stories.html'), encoding='utf-8').read(); ns = open(os.path.join(OUT, 'stories.html'), encoding='utf-8').read()
def sec(s, n):
    i = s.index('<section class="chap" id="c%s"' % n); return s[i:s.index('</section>', i)]
ok('old chapter sections c1..c%s byte-identical' % len(B['CH']), all(sec(bs, n) == sec(ns, n) for n in B['CH']))
# old audio untouched
bad = []
for acc in ('us', 'uk'):
    for f in os.listdir(os.path.join(BASE, 'audio', acc)):
        a = os.path.join(BASE, 'audio', acc, f); b = os.path.join(OUT, 'audio', acc, f)
        if os.path.getsize(a) != os.path.getsize(b) or open(a, 'rb').read() != open(b, 'rb').read(): bad.append(f)
ok('old audio files byte-identical', not bad, '%d bad' % len(bad))
BB = lambda p: json.loads(open(p, encoding='utf-8').read().strip()[len('var BOUNDS='):].rstrip(';'))
bo, bn = BB(os.path.join(BASE, 'data/bounds.js')), BB(os.path.join(OUT, 'data/bounds.js'))
ok('old BOUNDS keys identical', all(bo[a][k] == bn[a][k] for a in bo for k in bo[a]))
keys = lambda s: sorted(set(re.findall(r"""(?:ld|sv|load|save|getItem|setItem)\(\s*['"]((?:wsv2|wsx)[\w-]*)['"]""", s)) | set(re.findall(r"""['"]((?:wsv2|wsx)-[\w-]+)['"]""", s)))
for f in ('stories.html', 'anki.html', 'index.html'):
    a = open(os.path.join(BASE, f), encoding='utf-8').read(); b = open(os.path.join(OUT, f), encoding='utf-8').read()
    ok('localStorage keys unchanged in ' + f, keys(a) == keys(b), str(keys(b)))
# ---- browser
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
def serve(d):
    h = functools.partial(Q, directory=d); s = socketserver.ThreadingTCPServer(('127.0.0.1', 0), h); s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start(); return 'http://127.0.0.1:%d/' % s.server_address[1]
ub, uo = serve(BASE), serve(OUT)
from playwright.sync_api import sync_playwright
import random
random.seed(7)
learned = random.sample(old, 300)
now = 1761300000000
state = {'v': 1, 'cards': {}, 'cfg': {'newPerDay': 20, 'dir': 'both', 'cloze': 1, 'theme': '', 'star': 0, 'nw': 0, 'acc': 'uk', 'order': 'story'}, 'day': {}, 'log': []}
for i, k in enumerate(learned):
    state['cards'][k] = {'q': 'r', 'iv': 3 + i % 30, 'ef': 2.5, 'due': now + (i % 9) * 86400000, 'reps': 2, 'lap': 0}
    if i % 3 == 0: state['cards']['r' + k] = {'q': 'l', 'iv': 0, 'ef': 2.3, 'due': now, 'reps': 1, 'lap': 1, 'st': 1}
ST = json.dumps(state)
errs = []
HOOK = 'window.__t={bq:function(){return buildQueue()},cids:function(){return cids()},S:function(){return S}};function pick(){'
def hook(route):
    r = route.fetch(); body = r.text()
    assert body.count('function pick(){') == 1
    route.fulfill(response=r, body=body.replace('function pick(){', HOOK, 1))  # test-only instrumentation, not shipped
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
    def queue(url, cfg_extra=None):
        ctx = br.new_context(); ctx.route('**/anki.html', hook); pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(url + ' ' + str(e)))
        pg.add_init_script('if(!sessionStorage.getItem("seeded")){localStorage.setItem("wsv2-anki",%s);sessionStorage.setItem("seeded","1")}' % json.dumps(ST))
        pg.goto(url + 'anki.html'); pg.wait_for_timeout(600)
        r = pg.evaluate('''()=>{__t.S().cfg.newPerDay=1e9;var q=__t.bq();var all=__t.cids();return {nw:q.nw,learn:q.learn,rev:q.rev,cids:all,stored:localStorage.getItem("wsv2-anki")}}''')
        ctx.close(); return r
    qb, qn = queue(ub), queue(uo)
    oldset = set(qb['cids'])
    ok('old card ids all still present', oldset <= set(qn['cids']), '%d old card ids (en+r)' % len(oldset))
    ok('new card ids are only new words', all(re.sub('^r', '', c) in newids for c in set(qn['cids']) - oldset), '%d new card ids' % len(set(qn['cids']) - oldset))
    ok('old cards keep identical new-card order', [c for c in qn['nw'] if c in oldset] == qb['nw'], '%d old new-cards' % len(qb['nw']))
    ok('learn/review queues identical', qb['learn'] == qn['learn'] and qb['rev'] == qn['rev'], 'learn %d rev %d' % (len(qb['learn']), len(qb['rev'])))
    ok('saved progress untouched by loading new page (cards)', json.loads(qn['stored'])['cards'] == state['cards'])
    nwn = [c for c in qn['nw'] if c not in oldset]
    lk = [N['W'][re.sub('^r', '', c)]['lk'] for c in nwn]
    ok('new words come first and newest-date-first', qn['nw'][:len(nwn)] == nwn and lk == sorted(lk, reverse=True), 'first: ' + ', '.join('%s(%s)' % (N['W'][re.sub('^r', '', c)]['w'], N['W'][re.sub('^r', '', c)]['ld']) for c in nwn[:4]))
    # screenshots
    shots = []
    for dev, vp, mob in (('desktop', {'width': 1366, 'height': 900}, False), ('mobile', {'width': 390, 'height': 844}, True)):
        for th in ('light', 'dark'):
            ctx = br.new_context(viewport=vp, is_mobile=mob, has_touch=mob, device_scale_factor=2 if mob else 1); ctx.route('**/anki.html', hook)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.add_init_script('localStorage.setItem("wsv2-theme","%s");if(!sessionStorage.getItem("s")){localStorage.setItem("wsv2-anki",JSON.stringify({v:1,cards:{},cfg:{newPerDay:20,dir:"en",cloze:1,theme:"",star:0,nw:0,acc:"us",order:"story"},day:{},log:[]}));sessionStorage.setItem("s","1")}' % th)
            pg.goto(uo + 'stories.html#c54'); pg.wait_for_timeout(2500); pg.evaluate('document.getElementById("c54").scrollIntoView()'); pg.wait_for_timeout(500)
            assert pg.evaluate('document.documentElement.getAttribute("data-theme")') == th
            f = os.path.join(SHOTS, 'stories_c54_%s_%s.png' % (dev, th)); pg.screenshot(path=f); shots.append(f)
            pg.click('#w1068-0'); pg.wait_for_timeout(400)
            f = os.path.join(SHOTS, 'popup_new_%s_%s.png' % (dev, th)); pg.screenshot(path=f); shots.append(f)
            pg.keyboard.press('Escape')
            pg.evaluate('document.querySelector("#c69 details.wl").scrollIntoView()'); pg.wait_for_timeout(1500)
            f = os.path.join(SHOTS, 'wordlist_c69_%s_%s.png' % (dev, th)); pg.screenshot(path=f); shots.append(f)
            if dev == 'desktop':
                pg.evaluate('document.querySelector(\'#toc a[href="#c54"]\').scrollIntoView({block:"center"})'); pg.wait_for_timeout(1500)
                f = os.path.join(SHOTS, 'toc_%s_%s.png' % (dev, th)); pg.screenshot(path=f); shots.append(f)
            pg.goto(uo + 'anki.html'); pg.wait_for_timeout(800)
            f = os.path.join(SHOTS, 'anki_%s_%s.png' % (dev, th)); pg.screenshot(path=f, full_page=False); shots.append(f)
            pg.evaluate('document.querySelector("#showB")&&document.querySelector("#showB").click()'); pg.wait_for_timeout(300)
            f = os.path.join(SHOTS, 'anki_back_%s_%s.png' % (dev, th)); pg.screenshot(path=f, full_page=True); shots.append(f)
            first = pg.evaluate('__t.bq().nw[0]')
            ok('anki first new card is newest batch word (%s %s)' % (dev, th), N['W'][re.sub('^r', '', first)].get('ld') == '10/23', first + ' ' + N['W'][re.sub('^r', '', first)]['w'])
            opts = pg.evaluate('[...document.querySelectorAll("#fBatch option")].map(o=>o.textContent)')
            ok('batch filter present (%s %s)' % (dev, th), any('10/23 新增' in o for o in opts), str(opts))
            pg.goto(uo + 'index.html'); pg.wait_for_timeout(400)
            f = os.path.join(SHOTS, 'index_%s_%s.png' % (dev, th)); pg.screenshot(path=f); shots.append(f)
            ctx.close()
    # quiz works on a new chapter
    ctx = br.new_context(); pg = ctx.new_page(); pg.goto(uo + 'stories.html#c60'); pg.wait_for_timeout(500)
    pg.evaluate('''()=>{var q=document.querySelector('#c60 .quiz');q.querySelectorAll('li').forEach(li=>{li.querySelector('input').value=li.getAttribute('data-a')});q.querySelector('.chk').click()}''')
    sc = pg.evaluate('document.querySelector("#c60 .quiz .score").textContent'); ok('new chapter quiz checks correctly', '5' in sc, sc)
    # audio for new segment & word resolves
    for u in ('audio/us/c54p0.mp3', 'audio/uk/c69p0.mp3', 'audio/us/w1068.mp3', 'audio/uk/x1365_1.mp3'):
        r = pg.request.get(uo + u); ok('audio served ' + u, r.ok and len(r.body()) > 1000, str(len(r.body())))
    ctx.close(); br.close()
ok('no JS page errors', not errs, '; '.join(errs[:5]))
json.dump(res, open(os.path.join(SHOTS, '..', 'verify_report.json'), 'w'), ensure_ascii=False, indent=1)
print('ALL PASS' if all(v['pass'] for v in res.values()) else 'SOME FAIL', len(res), 'checks')
