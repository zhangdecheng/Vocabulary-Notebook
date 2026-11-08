#!/usr/bin/env python3
"""Regression: cold-opening #cN must not retarget 继续阅读 away from a saved chapter.

Seed is a real old paragraph, c12p1. Expected behavior matches base
018ad919b548947b5dd219c94660419d662ca071: after scripts paint the continue
control, it still points at chapter 12 paragraph 2. The pre-existing scroll
autosave may later rewrite wsx-last; this test does not treat that as the
new bug. It fails if boot navigation writes an empty paragraph or the
continue control leaves chapter 12.
"""
import datetime, functools, http.server, json, os, socketserver, subprocess, sys, threading
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SEED = {"c": 12, "p": "c12p1", "t": 1700000000000}
SEED_RAW = json.dumps(SEED, separators=(",", ":"))

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return

def main():
    sha = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Handler, directory=SITE))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    url = "http://127.0.0.1:%d/stories.html" % port
    print("ENV sha %s utc %s chrome-local port %s pid %s" % (sha, started, port, os.getpid()))
    print("SEED %s" % SEED_RAW)
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
            for fragment in ("#c1", "#c35"):
                ctx = browser.new_context(viewport={"width": 1366, "height": 900})
                page = ctx.new_page()
                writes = []
                page.add_init_script("""(() => {
                  const orig = Storage.prototype.setItem;
                  const log = [];
                  Storage.prototype.setItem = function(k, v) {
                    if (k === 'wsx-last') log.push(String(v));
                    return orig.call(this, k, v);
                  };
                  window.__lsWrites = log;
                  localStorage.setItem('wsx-last', %s);
                })();""" % json.dumps(SEED_RAW))
                page.goto(url + fragment, wait_until="load")
                page.wait_for_timeout(250)
                early = page.evaluate("""() => ({
                  hash: location.hash,
                  cont: document.querySelector('#cont').innerText,
                  c: document.querySelector('#cont').getAttribute('data-c'),
                  p: document.querySelector('#cont').getAttribute('data-p'),
                  raw: localStorage.getItem('wsx-last'),
                  writes: window.__lsWrites.slice(),
                  h2: (function(){
                    var id = location.hash.slice(1);
                    var el = document.getElementById(id);
                    var h = el && el.querySelector('h2');
                    var bar = document.querySelector('#toolbar') || document.querySelector('.tb');
                    var hr = h ? h.getBoundingClientRect() : null;
                    var br = bar ? bar.getBoundingClientRect() : null;
                    var sticky = br ? br.bottom : 0;
                    return hr ? {top: hr.top, bottom: hr.bottom, sticky: sticky, text: h.innerText,
                      visible: hr.bottom > sticky && hr.top < innerHeight} : null;
                  })()
                })""")
                page.wait_for_timeout(2500)
                late = page.evaluate("""() => ({
                  c: document.querySelector('#cont').getAttribute('data-c'),
                  p: document.querySelector('#cont').getAttribute('data-p'),
                  cont: document.querySelector('#cont').innerText,
                  raw: localStorage.getItem('wsx-last'),
                  writes: window.__lsWrites.slice()
                })""")
                empty_write = any('"p":""' in w or '"p": ""' in w for w in late["writes"])
                ok_button = early["c"] == "12" and early["p"] == "c12p1" and late["c"] == "12" and late["p"] == "c12p1"
                ok_visible = bool(early["h2"] and early["h2"]["visible"])
                ok_empty = not empty_write
                passed = ok_button and ok_visible and ok_empty
                row = {
                    "fragment": fragment,
                    "expected": {"contC": "12", "contP": "c12p1", "emptyParagraphWrite": False, "headingVisible": True},
                    "actualEarly": early,
                    "actualLate": late,
                    "emptyParagraphWrite": empty_write,
                    "pass": passed,
                }
                results.append(row)
                print("CASE", fragment, "PASS" if passed else "FAIL")
                print("  expected continue data-c=12 data-p=c12p1, no wsx-last write with empty p, heading visible")
                print("  actual early c=%s p=%r visible=%s" % (early["c"], early["p"], ok_visible))
                print("  actual late  c=%s p=%r storage=%s" % (late["c"], late["p"], late["raw"]))
                print("  empty p write %s" % empty_write)
                print("  writes %s" % json.dumps(late["writes"], ensure_ascii=False))
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    failed = [r["fragment"] for r in results if not r["pass"]]
    print("RESULT", "PASS" if not failed else "FAIL " + ",".join(failed))
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
