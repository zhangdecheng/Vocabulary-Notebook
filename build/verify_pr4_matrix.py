#!/usr/bin/env python3
"""Ethan recheck matrix for PR 4. Local HTTP only. Audio responses are aborted, not downloaded."""
import datetime, functools, hashlib, http.server, json, os, re, socketserver, subprocess, threading, time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = "/opt/cursor/artifacts/pr4-recheck"
SHOTS = os.path.join(OUT, "shots")
BASE_SHA = "018ad919b548947b5dd219c94660419d662ca071"
os.makedirs(SHOTS, exist_ok=True)

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def git_show(path):
    return subprocess.check_output(["git", "-C", ROOT, "show", BASE_SHA + ":" + path])

BASE_HTML = git_show("site/stories.html").decode("utf-8")
HEAD_HTML = open(os.path.join(SITE, "stories.html"), encoding="utf-8").read()
SHA = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()

class Handler(http.server.SimpleHTTPRequestHandler):
    variant = "head"
    def log_message(self, *a):
        return
    def do_GET(self):
        if self.path.split("?", 1)[0] == "/stories.html" and self.variant == "base":
            body = BASE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

def serve(variant):
    cls = type("H", (Handler,), {"variant": variant})
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(cls, directory=SITE))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

def chap(html, n):
    m = re.search(r'<section class="chap[^"]*" id="c%d"' % n, html)
    if not m:
        return None
    b = html.find("</section>", m.end())
    return html[m.start():b + len("</section>")]

def visible_js(id_expr):
    return """() => {
      const el = document.getElementById(%s);
      const bar = document.querySelector('#toolbar') || document.querySelector('.tb');
      const sticky = bar ? bar.getBoundingClientRect().bottom : 0;
      if (!el) return {exists:false};
      const h = el.querySelector('h2') || el;
      const r = h.getBoundingClientRect();
      const covered = r.bottom <= sticky || r.top >= innerHeight;
      return {exists:true, tag:h.tagName, text:(h.innerText||'').slice(0,80), top:r.top, bottom:r.bottom, sticky:sticky,
        visible: r.bottom > sticky && r.top < innerHeight && r.height > 0, coveredBySticky: r.bottom <= sticky && r.bottom > 0};
    }""" % json.dumps(id_expr) if False else None

VIS = """(id) => {
  const el = document.getElementById(id);
  const bar = document.querySelector('#toolbar') || document.querySelector('.tb');
  const sticky = bar ? bar.getBoundingClientRect().bottom : 0;
  if (!el) return {exists:false, id};
  const h = el.matches && el.classList.contains('para') ? el : (el.querySelector('h2') || el);
  const r = h.getBoundingClientRect();
  return {exists:true, id, tag:h.tagName, text:(h.innerText||'').replace(/\\s+/g,' ').slice(0,90),
    top:Math.round(r.top), bottom:Math.round(r.bottom), sticky:Math.round(sticky), height:Math.round(r.height),
    visible: r.height > 0 && r.bottom > sticky && r.top < innerHeight};
}"""

rows = []
def add(item, expected, actual, ok, note=""):
    rec = {"item": item, "expected": expected, "actual": actual, "pass": bool(ok), "utc": utc(), "note": note}
    rows.append(rec)
    print(("PASS " if ok else "FAIL ") + item)
    if not ok:
        print("  expected", expected)
        print("  actual", actual)

def plain_en(html_fragment):
    text = re.sub(r"<i class=\"gl\">.*?</i>", "", html_fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&#x27;", "'").replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()

def story_paragraphs():
    text = open(os.path.join(ROOT, "build/week-1102/story.md"), encoding="utf-8").read()
    text = text.split("## 白板用词提示")[0]
    text = "## 第 1 章" + text.split("## 第 1 章", 1)[1]
    paras = []
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("### ") or line.startswith("> ") or not line.strip():
            continue
        paras.append(re.sub(r"\s+", " ", re.sub(r"\*\*([^*]+)\*\*", r"\1", line.strip())))
    return paras

def main():
    t0 = time.time()
    print("MATRIX sha", SHA, "base", BASE_SHA, "utc", utc(), "pid", os.getpid())
    # ---- 1 static old chapters
    same = []
    differ = []
    for n in range(1, 70):
        a, b = chap(BASE_HTML, n), chap(HEAD_HTML, n)
        if a == b:
            same.append(n)
        else:
            differ.append(n)
    add("1 old c1-c69 section bytes vs base", "69 identical", {"identical": len(same), "differ": differ}, differ == [])
    add("1 anchors c1-c69 once", "each once", {str(n): HEAD_HTML.count('id="c%d"' % n) for n in (1, 35, 69)},
        all(HEAD_HTML.count('id="c%d"' % n) == 1 for n in range(1, 70)))
    for rel in ("site/data/words.json", "site/data/words.js", "site/data/bounds.js", "site/anki.html", "site/index.html"):
        disk = open(os.path.join(ROOT, rel), "rb").read()
        base = git_show(rel)
        add("1 %s unchanged" % rel, "sha256 match base", hashlib.sha256(disk).hexdigest(), disk == base)
    # audio directory not in the diff of this branch vs base
    diff_names = subprocess.check_output(["git", "-C", ROOT, "diff", "--name-only", BASE_SHA, "HEAD"], text=True).split()
    # working tree too
    wt = subprocess.check_output(["git", "-C", ROOT, "diff", "--name-only"], text=True).split()
    audio_touched = [n for n in diff_names + wt if n.startswith("site/audio/")]
    add("1 no audio files in branch or worktree diff", [], audio_touched, audio_touched == [])

    # ---- 3 static coverage
    wk = open(os.path.join(SITE, "data/week-1102.js"), encoding="utf-8").read()
    data = json.loads(wk[len("var WEEK="):-2] if wk.endswith(";\n") else wk[len("var WEEK="):-1])
    counts = {k: len(v) for k, v in data["CH"].items()}
    expect_counts = {"70": 32, "71": 82, "72": 72, "73": 22, "74": 44}
    ids = [i for k in ("70", "71", "72", "73", "74") for i in data["CH"][k]]
    add("3 chapter counts", expect_counts, counts, counts == expect_counts)
    add("3 252 unique k1102 ids", 252, {"n": len(ids), "unique": len(set(ids))}, len(ids) == 252 and len(set(ids)) == 252)
    add("3 w1102 unique", 1, HEAD_HTML.count('id="w1102"'), HEAD_HTML.count('id="w1102"') == 1)
    week = re.search(r"<!--w11-body-->(.*)<!--/w11-body-->", HEAD_HTML, re.S).group(1)
    ens = re.findall(r'<p class="en" lang="en">(.*?)</p>', week, re.S)
    got = [plain_en(x) for x in ens]
    src = story_paragraphs()
    mismatch = [(i, src[i][:80], got[i][:80]) for i in range(min(len(src), len(got))) if src[i] != got[i]]
    add("3 English body matches story source", {"paras": len(src)}, {"paras": len(got), "mismatch": mismatch[:5]}, got == src)
    mew = data["W"].get("k1102-015")  # coverage order: item 15 is Mewali? verify by word
    mew = next(v for v in data["W"].values() if v["w"] == "Mewali")
    add("3 Mewali unverified and not taught as 不客气", "未核验, no 不客气 in card", mew["z"], ("未核验" in mew["z"] and "不客气" not in mew["z"] and "不客气" not in week))

    servers = {"base": serve("base"), "head": serve("head")}
    print("SERVERS", {k: v.server_address[1] for k, v in servers.items()}, "parent pid", os.getpid())
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
            # ---- 1 + 5 + 2 browser
            def new_page(width=1366, height=900, mobile=False, theme="light", storage=None):
                kw = {"viewport": {"width": width, "height": height}}
                if mobile:
                    kw.update(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
                               is_mobile=True, has_touch=True, device_scale_factor=2)
                ctx = browser.new_context(**kw)
                pg = ctx.new_page()
                audio = []
                blocked = []
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                def route(route):
                    u = route.request.url
                    if "/audio/" in u:
                        audio.append(u)
                        route.abort()
                        return
                    if not u.startswith("http://127.0.0.1"):
                        blocked.append(u)
                        route.abort()
                        return
                    route.continue_()
                pg.route("**/*", route)
                seed_js = """(() => {
                  window.__tts = [];
                  const ss = window.speechSynthesis || {};
                  ss.speak = function(u){ window.__tts.push(String(u && u.text || '')); };
                  ss.cancel = function(){};
                  window.speechSynthesis = ss;
                  if (!sessionStorage.getItem('matrix-seeded')) {
                    localStorage.setItem('wsv2-theme', %s);
                    %s
                    sessionStorage.setItem('matrix-seeded', '1');
                  }
                })();""" % (json.dumps(theme), storage or "")
                pg.add_init_script(seed_js)
                return ctx, pg, audio, blocked, errors

            # old audio URL via intercepted click, US and UK, head and the path shape
            ctx, pg, audio, blocked, errors = new_page()
            pg.goto("http://127.0.0.1:%d/stories.html#c1" % servers["head"].server_address[1], wait_until="load")
            pg.wait_for_timeout(400)
            pg.evaluate("document.fonts && document.fonts.ready")
            wid = pg.locator("#c1 .pw").first.get_attribute("data-i")
            pg.locator("#c1 .say").first.click()
            pg.wait_for_timeout(300)
            say_urls = list(audio)
            audio.clear()
            pg.locator("#c1 .pw[data-acc=us]").first.click()
            pg.wait_for_timeout(200)
            us_word = list(audio)
            audio.clear()
            # switch UK through the real accent control
            pg.locator("#gear").click()
            pg.locator('#accsw button[data-v="uk"]').click()
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            pg.locator("#c1 .pw[data-acc=uk]").first.click()
            pg.wait_for_timeout(200)
            uk_word = list(audio)
            add("1 old paragraph click requests audio/us/c1p0.mp3 and is aborted", ["/audio/us/c1p0.mp3"], say_urls,
                say_urls == ["http://127.0.0.1:%d/audio/us/c1p0.mp3" % servers["head"].server_address[1]] or [u for u in say_urls if u.endswith("/audio/us/c1p0.mp3")] == say_urls and len(say_urls) >= 1)
            add("1 old US word click requests audio/us/w%s.mp3" % wid, "w%s" % wid, us_word, any(u.endswith("/audio/us/w%s.mp3" % wid) for u in us_word))
            add("1 old UK word click requests audio/uk/w%s.mp3" % wid, "w%s" % wid, uk_word, any(u.endswith("/audio/uk/w%s.mp3" % wid) for u in uk_word))
            add("1 old-chapter pageerrors", [], errors, errors == [])
            ctx.close()

            # base vs head cold open visibility + progress
            seed_last = "localStorage.setItem('wsx-last', %s);" % json.dumps(json.dumps({"c": 12, "p": "c12p1", "t": 1700000000000}))
            targets = [("base", "c1"), ("base", "c35"), ("base", "c69"), ("base", "c12p1"),
                       ("head", "c1"), ("head", "c35"), ("head", "c69"), ("head", "c70"), ("head", "c74"), ("head", "w1102"), ("head", "c12p1")]
            for variant, tid in targets:
                ctx, pg, audio, blocked, errors = new_page(storage=seed_last)
                pg.goto("http://127.0.0.1:%d/stories.html#%s" % (servers[variant].server_address[1], tid), wait_until="load")
                pg.wait_for_timeout(500)
                pg.evaluate("document.fonts && document.fonts.ready")
                pg.wait_for_timeout(300)
                vis = pg.evaluate(VIS, tid)
                cont = pg.evaluate("""() => ({c:document.querySelector('#cont').getAttribute('data-c'), p:document.querySelector('#cont').getAttribute('data-p'), text:document.querySelector('#cont').innerText, raw:localStorage.getItem('wsx-last')})""")
                progress_ok = cont["c"] == "12" and cont["p"] == "c12p1"
                # Chapter hashes on head are aligned after layout. Paragraph hashes and base deep links
                # are recorded against each other later; progress must stay on the saved chapter.
                need_visible = variant == "head" and tid in ("c1", "c35", "c69", "c70", "c74", "w1102")
                add("2 %s cold #%s progress kept%s" % (variant, tid, " and heading visible" if need_visible else ""),
                    {"progress": "12/c12p1", "visible": True if need_visible else "recorded"},
                    {"visible": vis, "cont": cont, "pageerrors": errors, "audio": audio},
                    progress_ok and not errors and (vis.get("visible") if need_visible else True),
                    "browser emulation, not a physical phone")
                ctx.close()

            # forward back refresh on head
            base_url = "http://127.0.0.1:%d/stories.html" % servers["head"].server_address[1]
            ctx, pg, audio, blocked, errors = new_page(storage=seed_last)
            pg.goto(base_url + "#c70", wait_until="load")
            pg.wait_for_timeout(300)
            pg.evaluate("document.querySelector('#chbar .cbn').click()")
            pg.wait_for_timeout(300)
            bar = pg.evaluate("""() => ({hash:location.hash, cur:__nav.cur(), c:document.querySelector('#cont').getAttribute('data-c'), p:document.querySelector('#cont').getAttribute('data-p')})""")
            add("2 chapter bar next keeps continue control", "hash #c71 continue 12/c12p1", bar, bar["hash"] == "#c71" and bar["cur"] == 71 and bar["c"] == "12" and bar["p"] == "c12p1")
            ctx.close()
            ctx, pg, audio, blocked, errors = new_page(storage=seed_last)
            pg.goto(base_url + "#c70", wait_until="load")
            pg.wait_for_timeout(200)
            pg.goto(base_url + "#c71", wait_until="load")
            pg.wait_for_timeout(300)
            pg.go_back(wait_until="load")
            pg.wait_for_timeout(500)
            back = pg.evaluate(VIS, "c70")
            back_cont = pg.evaluate("""() => ({hash:location.hash, c:document.querySelector('#cont').getAttribute('data-c'), p:document.querySelector('#cont').getAttribute('data-p')})""")
            pg.go_forward(wait_until="load")
            pg.wait_for_timeout(500)
            fwd = pg.evaluate(VIS, "c71")
            fwd_cont = pg.evaluate("""() => ({hash:location.hash, c:document.querySelector('#cont').getAttribute('data-c'), p:document.querySelector('#cont').getAttribute('data-p')})""")
            pg.reload(wait_until="load")
            pg.wait_for_timeout(500)
            rel = pg.evaluate(VIS, "c71")
            rel_cont = pg.evaluate("""() => ({hash:location.hash, c:document.querySelector('#cont').getAttribute('data-c'), p:document.querySelector('#cont').getAttribute('data-p')})""")
            add("2 browser back to #c70", "hash #c70 and continue still 12/c12p1 during this visit", {"vis": back, "cont": back_cont}, back_cont["hash"] == "#c70" and back_cont["c"] == "12" and back_cont["p"] == "c12p1", "scroll restoration is the browser's, not boot; heading position is recorded in vis")
            add("2 browser forward to #c71", "hash #c71 and continue still 12/c12p1 during this visit", {"vis": fwd, "cont": fwd_cont}, fwd_cont["hash"] == "#c71" and fwd_cont["c"] == "12" and fwd_cont["p"] == "c12p1", "same scroll-restoration note as back")
            add("2 reload after hashchange", "record only; base hashchange also remember(chapter, '') so a later reload can paint that", {"vis": rel, "cont": rel_cont}, rel_cont["hash"] == "#c71", "not asserted as a new regression; see base history probe")
            ctx.close()

            # ---- 4 learned / anki
            anki = {"v": 1, "cards": {"2": {"q": "r", "iv": 30}, "4": {"q": "r", "iv": 10}, "r5": {"q": "r", "iv": 21}}, "cfg": {}, "day": {}, "log": []}
            learned0 = {"13": 1, "40": 1}
            storage = (
                "localStorage.setItem('wsx-learned', %s);" % json.dumps(json.dumps(learned0))
                + "localStorage.setItem('wsv2-anki', %s);" % json.dumps(json.dumps(anki))
                + "localStorage.setItem('wsx-last', %s);" % json.dumps(json.dumps({"c": 12, "p": "c12p1", "t": 1700000000000}))
            )
            ctx, pg, audio, blocked, errors = new_page(storage=storage)
            pg.goto(base_url + "#c1", wait_until="load")
            pg.wait_for_timeout(300)
            before_n = pg.locator("#learnedN").inner_text()
            denom = pg.locator("#prog").inner_text()
            # one old word not already counted, three new words
            for iid in ("1", "k1102-001", "k1102-032", "k1102-050"):
                pg.locator('input.lrn[data-i="%s"]' % iid).evaluate("el => el.click()")
            pg.wait_for_timeout(200)
            after_click = pg.evaluate("""() => ({n:document.querySelector('#learnedN').textContent, learned:JSON.parse(localStorage.getItem('wsx-learned')), anki:JSON.parse(localStorage.getItem('wsv2-anki'))})""")
            pg.reload(wait_until="load")
            pg.wait_for_timeout(400)
            after = pg.evaluate("""() => ({n:document.querySelector('#learnedN').textContent, denom:document.querySelector('#prog').innerText, learned:JSON.parse(localStorage.getItem('wsx-learned')), anki:JSON.parse(localStorage.getItem('wsv2-anki')), c1:document.querySelector('input.lrn[data-i=\"1\"]').checked, kn:document.querySelector('input.lrn[data-i=\"k1102-001\"]').checked})""")
            add("4 denominator stays / 1365", "1365", denom + " | " + after["denom"], "/ 1365" in denom and "/ 1365" in after["denom"])
            add("4 mastered old-word total increases by 1", str(int(before_n) + 1), {"before": before_n, "afterClick": after_click["n"], "afterReload": after["n"]},
                after["n"] == after_click["n"] == str(int(before_n) + 1))
            kept = all(after["learned"].get(k) == 1 for k in ("13", "40", "1", "k1102-001", "k1102-032", "k1102-050"))
            add("4 old learned keys kept and new keys stored", "13,40,1 and 3 k1102", sorted(after["learned"]), kept and after["c1"] and after["kn"])
            add("4 anki blob unchanged", anki, after["anki"], after["anki"] == anki)
            ctx.close()

            # ---- 5 new chapter audio entry points
            ctx, pg, audio, blocked, errors = new_page()
            pg.goto(base_url + "#c70", wait_until="load")
            pg.wait_for_timeout(400)
            dom = pg.evaluate("""() => ({
              say: document.querySelectorAll('#c70 .say').length,
              sayall: document.querySelectorAll('#c70 .sayall').length,
              pw: document.querySelectorAll('#c70 .pw').length,
              na: document.querySelector('#c70 .ch-meta').innerText,
              table: document.querySelector('#c70 .pr').innerText
            })""")
            pg.locator("#c70 .tw").first.focus()
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(200)
            pop = pg.locator("#pop").inner_text()
            pg.keyboard.press(" ")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(200)
            tts = pg.evaluate("window.__tts")
            add("5 new chapter has no say/sayall/pw controls", {"say": 0, "sayall": 0, "pw": 0}, dom, dom["say"] == dom["sayall"] == dom["pw"] == 0 and "暂无朗读" in dom["na"] and "暂无" in dom["table"])
            add("5 card and keyboard show 暂无音频 and make no audio/TTS request", {"audio": [], "tts": [], "popHas": "暂无音频"},
                {"audio": audio, "tts": tts, "pop": pop[:180], "errors": errors},
                "暂无音频" in pop and audio == [] and tts == [] and "美式" not in pop and errors == [])
            ctx.close()

            # ---- 6 screenshots and layout, emulation
            shots = [
                ("desktop", False, "light", 1366, 900, "c70", "06-desktop-light-card"),
                ("desktop", False, "dark", 1366, 900, "c74", "06-desktop-dark-continue"),
                ("mobile-390", True, "light", 390, 844, "c70", "06-mobile390-light-toc"),
                ("mobile-390", True, "dark", 390, 844, "c74", "06-mobile390-dark-card"),
            ]
            for name, mobile, theme, w, h, tid, shot in shots:
                ctx, pg, audio, blocked, errors = new_page(width=w, height=h, mobile=mobile, theme=theme, storage=seed_last)
                pg.goto(base_url + "#" + tid, wait_until="load")
                pg.wait_for_timeout(500)
                pg.evaluate("document.fonts && document.fonts.ready")
                theme_ok = pg.evaluate("document.documentElement.getAttribute('data-theme')") == theme
                overflow = pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                cont = pg.evaluate("""() => { const e=document.querySelector('#cont'); const r=e.getBoundingClientRect(); return {text:e.innerText, c:e.getAttribute('data-c'), p:e.getAttribute('data-p'), top:r.top, bottom:r.bottom, visible:r.bottom>0 && r.top<innerHeight}; }""")
                if "toc" in shot:
                    pg.locator("#menu").click()
                    pg.wait_for_timeout(400)
                    toc_txt = pg.locator("#toc").inner_text()
                    toc_open = pg.evaluate("document.body.classList.contains('toc-open')")
                    add("6 %s %s toc open and lists new group" % (name, theme), "11/02–11/08 and c74", {"open": toc_open, "has": "11/02–11/08" in toc_txt}, toc_open and "11/02–11/08" in toc_txt and "74" in toc_txt)
                else:
                    pg.locator("#%s .tw" % ("c70" if tid == "c70" else "c74")).first.click()
                    pg.wait_for_timeout(250)
                    pop = pg.locator("#pop").inner_text()
                    add("6 %s %s word card 暂无音频" % (name, theme), "暂无音频", pop[:120], "暂无音频" in pop and "undefined" not in pop.lower())
                add("6 %s %s theme and no horizontal overflow" % (name, theme), theme, {"theme": theme_ok, "overflowOk": overflow}, theme_ok and overflow, "390px emulation" if mobile else "desktop emulation")
                add("6 %s %s continue control still chapter 12" % (name, theme), "12/c12p1", cont, cont["c"] == "12" and cont["p"] == "c12p1")
                path = os.path.join(SHOTS, shot + ".png")
                pg.screenshot(path=path)
                add("6 screenshot written " + shot, path, os.path.exists(path), os.path.exists(path))
                ctx.close()
            browser.close()
    finally:
        failed = [r for r in rows if not r["pass"]]
        report = {"sha": SHA, "base": BASE_SHA, "utc": utc(), "elapsedSec": round(time.time() - t0, 3), "rows": rows, "failed": [r["item"] for r in failed]}
        json.dump(report, open(os.path.join(OUT, "05-matrix.json"), "w"), ensure_ascii=False, indent=2)
        for name, httpd in servers.items():
            print("SHUTDOWN", name, "port", httpd.server_address[1])
            httpd.shutdown()
            httpd.server_close()
        print("RESULT", "PASS" if not failed else "FAIL %d" % len(failed), "of", len(rows))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
