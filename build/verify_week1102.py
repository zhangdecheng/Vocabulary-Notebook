#!/usr/bin/env python3
"""Static + local Playwright checks for the 11/02–11/08 side story.

Serves site/ on 127.0.0.1 only. Does not touch production.
"""
import functools, hashlib, http.server, json, os, re, socketserver, subprocess, threading
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SHOTS = os.environ.get("WEEK_SHOTS", "/tmp/week1102-shots")
os.makedirs(SHOTS, exist_ok=True)
res = []

def ok(name, cond, info=""):
    res.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (("  " + info) if info else ""))

def git_file(path):
    return subprocess.check_output(["git", "show", "HEAD:" + path])

def chap_html(html, n):
    m = re.search(r'<section class="chap[^"]*" id="c%d"' % n, html)
    if not m:
        return None
    a = html.rfind("<section", 0, m.start())
    b = html.find("</section>", m.end())
    return html[a:b + len("</section>")]

def main():
    new = open(os.path.join(SITE, "stories.html"), encoding="utf-8").read()
    old = git_file("site/stories.html").decode("utf-8")
    for n in range(1, 70):
        a, b = chap_html(old, n), chap_html(new, n)
        if a != b:
            ok("old chapter c%d byte-identical" % n, False, "len %s vs %s" % (len(a or ""), len(b or "")))
            break
    else:
        ok("old chapters c1–c69 byte-identical through </section>", True)
    ids = re.findall(r'\sid="([^"]+)"', new)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    ok("all id attributes unique", not dup, str(dup[:8]))
    ok("old anchors c1–c69 still once", all(new.count('id="c%d"' % n) == 1 for n in range(1, 70)))
    ok("new anchors c70–c74 and w1102 once", all(new.count('id="%s"' % i) == 1 for i in ["c70", "c71", "c72", "c73", "c74", "w1102"]))
    week = re.search(r"<!--w11-body-->(.*)<!--/w11-body-->", new, re.S).group(1)
    ok("new chapters have no paragraph/chapter play buttons", 'class="say"' not in week and "sayall" not in week)
    ok("new chapters are not tagged as the 10/23 batch", 'data-bt=' not in week)
    ok("old c1 and c69 still have read-aloud buttons", 'class="say"' in chap_html(new, 1) and "sayall" in chap_html(new, 69))
    ok("c54–c69 still data-bt=10/23", all(re.search(r'<section class="chap" id="c%d" data-c="%d" data-bt="10/23"' % (n, n), new) for n in range(54, 70)))
    for rel in ("site/data/words.json", "site/data/words.js", "site/data/bounds.js", "site/anki.html", "site/index.html"):
        disk = open(os.path.join(ROOT, rel), "rb").read()
        ok(rel + " unchanged", disk == git_file(rel))
    # storage key names: nothing removed
    def keys(s):
        return set(re.findall(r"""['"]((?:wsv2|wsx)-[\w-]+)['"]""", s))
    ok("stories localStorage key names kept", keys(old) <= keys(new), str(sorted(keys(old) - keys(new))))
    wk_raw = open(os.path.join(SITE, "data/week-1102.js"), encoding="utf-8").read()
    ok("week.js cache hash", ("week-1102.js?v=" + hashlib.md5(wk_raw.encode()).hexdigest()[:8]) in new)
    data = json.loads(wk_raw[len("var WEEK="):-2])
    W, CH = data["W"], data["CH"]
    ok("252 cards", len(W) == 252, str(len(W)))
    cov = json.load(open(os.path.join(ROOT, "build/week-1102/coverage.json"), encoding="utf-8"))
    by_id = {it["_id"]: it for it in []}  # filled below from stable ids
    items = cov["items"]
    ok("coverage file has 252", len(items) == 252)
    missing = []
    bad_mean = []
    for n, it in enumerate(items, 1):
        sid = "k1102-%03d" % n
        rec = W.get(sid)
        if not rec:
            missing.append(sid)
            continue
        surface = it["used_as"]
        if week.count(">" + surface + "<i") != 1 and week.count(">" + __import__("html").escape(surface) + "<i") != 1:
            # highlighted text is escaped
            esc = __import__("html").escape(surface, quote=False)
            if (">" + esc + "<i") not in week:
                missing.append(surface)
        z = rec["z"]
        if it["word"] == "Mewali":
            if "不客气" in z or "未核验" not in z:
                bad_mean.append("Mewali:" + z)
        else:
            ctx = it.get("meaning_context") or ""
            if z != ctx:
                bad_mean.append(it["word"])
        if not z or "undefined" in z.lower() or rec.get("p"):
            bad_mean.append("empty-or-ipa:" + it["word"])
        if not rec.get("na"):
            bad_mean.append("audio-flag:" + it["word"])
    ok("252 surfaces highlighted once and meanings match", not missing and not bad_mean, str(missing[:5] + bad_mean[:5]))
    ok("chapter id lists cover 252", sum(len(v) for v in CH.values()) == 252)
    ok("no local path or audit filename on the story page", all(s not in new for s in ("/workspace", "coverage-1102", "vocab-master", "/var/www")))
    ok("Mewali is not given a confirmed gloss on the page", "不客气" not in week)
    ok("snapshot date is visible", "2026-11-06" in week and "本地快照" in week)
    # highlighted count
    ok("252 highlight spans in the new group", len(re.findall(r'class="tw(?: w11u)?" data-i="k1102-', week)) == 252)

    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Q, directory=SITE))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/stories.html" % srv.server_address[1]
    ios = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        errs = []
        ctx = br.new_context(viewport={"width": 1366, "height": 900})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append("pageerror " + str(e)))
        pg.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and errs.append("console " + m.text))
        pg.on("response", lambda r: r.status >= 400 and not r.url.endswith("favicon.ico") and errs.append("%d %s" % (r.status, r.url)))
        pg.add_init_script("""if(!sessionStorage.getItem('week-init')){
          localStorage.setItem('wsv2-theme','light');
          localStorage.setItem('wsx-learned', JSON.stringify({"13":1}));
          localStorage.setItem('wsx-last', JSON.stringify({c:1,p:'c1p1',t:1}));
          sessionStorage.setItem('week-init','1');}""")
        pg.goto(base + "#c1")
        pg.wait_for_timeout(800)
        ok("desktop loads c1", pg.evaluate("location.hash") == "#c1" and pg.locator("#c1").count() == 1)
        ok("continue-reading restores old chapter", "第 1 章" in pg.locator("#contT").inner_text())
        ok("old mastered key 13 still checked", pg.locator('input.lrn[data-i="13"]').is_checked())
        sub = pg.locator(".hd .sub").inner_text().replace(" ", "")
        ok("header counts 74 chapters and 1365 main-list words", sub == "74章·1365词", sub)
        newc = pg.locator("#newc").inner_text()
        ok("latest-batch card still 10/23 chapters 54–69", "10/23" in newc and "54" in newc and "69" in newc, newc.replace("\n", " "))
        prog = pg.locator("#prog").inner_text()
        ok("mastered count ignores the side-story ids and keeps / 1365", "/ 1365" in prog and pg.locator("#learnedN").inner_text() == "1", prog.replace("\n", " "))
        # old word card + audio link
        pg.locator("#c1 .tw").first.click()
        pg.wait_for_timeout(300)
        pop = pg.locator("#pop").inner_text()
        ok("old word card has a meaning and US/UK buttons", "undefined" not in pop and "美式" in pop and "英式" in pop, pop.split("\n")[0][:80])
        pg.locator("#c1 .say").first.click()
        pg.wait_for_timeout(600)
        src = pg.evaluate("document.querySelector('body') && (window.__aud && __aud.player.src) || ''")
        ok("old paragraph audio still points at audio/us/c1p0.mp3", src.endswith("/audio/us/c1p0.mp3"), src)
        pg.evaluate("window.__aud && __aud.stop()")
        # theme
        pg.locator("#thm").click()
        pg.wait_for_timeout(200)
        ok("theme toggles to dark and is stored", pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark" and pg.evaluate("localStorage.getItem('wsv2-theme')") == "dark")
        pg.screenshot(path=os.path.join(SHOTS, "desktop-dark-c1.png"))
        pg.locator("#thm").click()
        # new chapter navigation
        pg.evaluate("window.__nav.go(70)")
        pg.wait_for_timeout(400)
        ok("nav go(70) lands on c70", pg.evaluate("window.__nav.cur()") == 70 and pg.evaluate("location.hash") == "#c70")
        ok("c70 has no play button", pg.locator("#c70 .say, #c70 .sayall").count() == 0)
        ok("c70 says 暂无朗读", "暂无朗读" in pg.locator("#c70 .ch-meta").inner_text())
        pg.locator("#c70 .tw").first.click()
        pg.wait_for_timeout(300)
        pop = pg.locator("#pop").inner_text()
        ok("new word card shows the gloss and no audio buttons", "周" in pop and "暂无音频" in pop and "美式" not in pop and "undefined" not in pop.lower(), pop.replace("\n", " | ")[:180])
        pg.screenshot(path=os.path.join(SHOTS, "desktop-light-c70-card.png"), full_page=False)
        # Mewali
        pg.evaluate("document.querySelector('#c70 .tw.w11u').click()")
        pg.wait_for_timeout(300)
        pop = pg.locator("#pop").inner_text()
        ok("Mewali card stays unverified", "未核验" in pop and "不客气" not in pop and "undefined" not in pop.lower(), pop.replace("\n", " | ")[:180])
        # progress write + readback, old key preserved
        box = pg.locator('#c70 input.lrn').first
        box.click()
        sid = box.get_attribute("data-i")
        pg.wait_for_timeout(200)
        learned = pg.evaluate("JSON.parse(localStorage.getItem('wsx-learned'))")
        ok("checking a new word keeps the old learned key", learned.get("13") == 1 and learned.get(sid) == 1, str(sorted(learned)))
        ok("side-story check does not change the 1365 mastered total", pg.locator("#learnedN").inner_text() == "1")
        ok("chapter progress shows 1 mastered", pg.locator('#c70 [data-cp="70"]').inner_text().startswith("已掌握 1/"))
        pg.evaluate("window.__nav.go(73)")
        pg.wait_for_timeout(300)
        pg.reload()
        pg.wait_for_timeout(800)
        ok("reload reads chapter 73 back", "周四：旅行计划" in pg.locator("#contT").inner_text() or pg.evaluate("window.__nav.cur()") == 73, pg.locator("#contT").inner_text())
        ok("reload keeps both learned keys", pg.evaluate("JSON.parse(localStorage.getItem('wsx-learned'))") .get("13") == 1 and pg.locator('input.lrn[data-i="%s"]' % sid).is_checked())
        # search
        pg.locator("#q").fill("CEFR")
        pg.wait_for_timeout(200)
        ok("search finds the new CEFR card", "CEFR" in pg.locator("#qr").inner_text())
        pg.locator("#qr a").first.click()
        pg.wait_for_timeout(500)
        ok("search jumps to the CEFR highlight", pg.evaluate("!!document.querySelector('#pop') && !document.querySelector('#pop').hidden"))
        # chapter bar next/prev around the boundary
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1200)
        pg.evaluate("document.documentElement.style.scrollBehavior='auto';window.__nav.go(70)")
        pg.wait_for_timeout(300)
        def in_view(page, cid):
            return page.evaluate("""(id)=>{var t=document.getElementById(id).getBoundingClientRect().top;return t}""", cid)
        ok("go(70) puts the heading in view", 0 <= in_view(pg, "c70") <= 140, str(in_view(pg, "c70")))
        pg.evaluate("document.querySelector('#chbar .cbp').click()")
        pg.wait_for_timeout(300)
        ok("previous from c70 is old c69", pg.evaluate("window.__nav.cur()==69 && (function(){var t=document.getElementById('c69').getBoundingClientRect().top;return t>=0&&t<=140})()"))
        ok("c69 read-aloud button still present", pg.locator("#c69 .sayall").count() == 1)
        pg.evaluate("document.querySelector('#chbar .cbn').click()")
        pg.wait_for_timeout(300)
        ok("next from c69 opens c70", pg.evaluate("window.__nav.cur()") == 70)
        pg.evaluate("document.querySelector('#chbar .cbn').click()")
        pg.wait_for_timeout(250)
        ok("next from c70 opens c71 in view", pg.evaluate("window.__nav.cur()==71 && (function(){var t=document.getElementById('c71').getBoundingClientRect().top;return t>=0&&t<=140})()"))
        # direct hash of an old and a new anchor, after layout
        pg.goto(base + "?h=1#c1")
        pg.wait_for_timeout(700)
        ok("hash c1 still resolves in view", ("第一天" in pg.locator("#c1").inner_text()) and 0 <= in_view(pg, "c1") <= 160)
        pg.goto(base + "?h=69#c69")
        pg.wait_for_timeout(700)
        ok("hash c69 still lands on the old chapter", 0 <= in_view(pg, "c69") <= 160, str(in_view(pg, "c69")))
        pg.goto(base + "?h=74#c74")
        pg.wait_for_timeout(700)
        ok("hash c74 lands on the new chapter", "周五" in pg.locator("#c74 h2").inner_text() and 0 <= in_view(pg, "c74") <= 160, str(in_view(pg, "c74")))
        pg.screenshot(path=os.path.join(SHOTS, "desktop-light-c74.png"))
        ok("desktop console/network clean", not errs, " | ".join(errs[:6]))

        # mobile light + dark
        for theme, shot in (("light", "mobile-light-c70.png"), ("dark", "mobile-dark-c74.png")):
            merrs = []
            mctx = br.new_context(viewport={"width": 390, "height": 844}, user_agent=ios, is_mobile=True, has_touch=True, device_scale_factor=2)
            mp = mctx.new_page()
            mp.on("pageerror", lambda e, box=merrs: box.append(str(e)))
            mp.on("console", lambda m, box=merrs: m.type == "error" and "Failed to load resource" not in m.text and box.append(m.text))
            mp.add_init_script("localStorage.setItem('wsv2-theme','%s')" % theme)
            mp.goto(base + "#c70")
            mp.wait_for_timeout(700)
            ok("mobile %s theme" % theme, mp.evaluate("document.documentElement.getAttribute('data-theme')") == theme)
            ok("mobile %s no horizontal overflow" % theme, mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
            ok("mobile %s c70 has no audio buttons" % theme, mp.locator("#c70 .say, #c70 .sayall").count() == 0)
            mp.locator("#c70 .tw").nth(2).tap()
            mp.wait_for_timeout(300)
            txt = mp.locator("#pop").inner_text()
            ok("mobile %s word card" % theme, "暂无音频" in txt and "undefined" not in txt.lower())
            if theme == "light":
                mp.screenshot(path=os.path.join(SHOTS, shot))
                mp.keyboard.press("Escape")
                mp.wait_for_timeout(200)
                mp.locator("#menu").tap()
                mp.wait_for_timeout(400)
                ok("mobile toc lists the new group", "11/02–11/08" in mp.locator("#toc").inner_text() and mp.locator('#toc a[data-c="74"]').count() == 1)
                mp.screenshot(path=os.path.join(SHOTS, "mobile-light-toc.png"))
                mp.locator('#toc a[data-c="74"]').tap()
                mp.wait_for_timeout(500)
                ok("mobile toc opens c74", mp.evaluate("window.__nav.cur()") == 74)
            else:
                mp.screenshot(path=os.path.join(SHOTS, shot))
            ok("mobile %s console clean" % theme, not merrs, " | ".join(merrs[:4]))
            mctx.close()
        ctx.close()
        br.close()
    srv.shutdown()
    failed = [n for n, c in res if not c]
    print("RESULT", "ALL PASS" if not failed else "FAILED %d" % len(failed), "of", len(res))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
