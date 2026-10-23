#!/usr/bin/env python3
"""
Leo in Bali 单词站 · 增量更新流水线
用法（见 README_更新说明.md）：
  python3 build/update.py --csv 新总表.csv --base site_base_dir --batch 10/23 --out out [--no-audio]
原则：已上线的旧词条（W 中已有的 id）、旧章节、旧音频、localStorage 键一律不改；只追加新词、新章节、新音频。
"""
import argparse, csv, html, json, os, re, shutil, sys, asyncio, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chapters import parse as parse_chapter, TAG

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = {'us': 'en-US-AvaNeural', 'uk': 'en-GB-SoniaNeural'}

def norm(w): return re.sub(r'\s+', ' ', html.unescape(w)).strip().lower()
def clean(w): return re.sub(r'\s+', ' ', html.unescape(w or '')).strip()
def esc(s): return html.escape(str(s), quote=True).replace('&#x27;', '&#x27;')

def load_csv(p):
    rows = list(csv.DictReader(open(p, encoding='utf-8-sig')))
    for r in rows:
        for k in list(r.keys()): r[k] = clean(r[k])
    return rows

def date_key(d, ystart=9):
    """'10/23' -> sortable int. 学期从 ystart 月开始：ystart..12 月算第 0 年，1..ystart-1 月算第 1 年。"""
    try: m, dd = [int(x) for x in d.split('/')[:2]]
    except Exception: return 0
    return (0 if m >= ystart else 1) * 10000 + m * 100 + dd

def read_js_var(path, var):
    s = open(path, encoding='utf-8').read().strip()
    s = s[len('var %s=' % var):]
    return json.loads(s.rstrip(';'))

# ---------------------------------------------------------------- diff
def diff(rows, W):
    live = {norm(v['w']): k for k, v in W.items()}
    new, changed, matched = [], [], set()
    for r in rows:
        n = norm(r['单词'])
        if n in live:
            k = live[n]; v = W[k]; matched.add(n); ch = []
            dates = [d.strip() for d in r['出现日期'].split(' / ') if d.strip()]
            if dates != v.get('d', []): ch.append('出现日期')
            if r['中文'] != v.get('z'): ch.append('中文')
            if r['主题'] not in v.get('t', []): ch.append('主题')
            if ch: changed.append({'id': k, 'w': v['w'], 'fields': ch})
        else:
            new.append(r)
    removed = [{'id': k, 'w': v['w']} for k, v in W.items() if norm(v['w']) not in matched]
    return new, changed, removed

# ---------------------------------------------------------------- text helpers
def plain(en):  # tagged paragraph -> plain English
    return TAG.sub(lambda m: m.group(1), en)

SENT = re.compile(r'(?<=[.!?])["”]?\s+(?=["“A-Z0-9])')
def sentences(text):
    out, last = [], 0
    for m in SENT.finditer(text):
        end = m.start() + (1 if text[m.start()] in '"”' else 0)
        out.append(text[last:m.end()].strip()); last = m.end()
    out.append(text[last:].strip())
    return [s for s in out if s]

def tts_word_text(w):
    t = w.replace('X% off', '10% off').replace(' / ', ', ').replace('…', ',').replace('[ ]', 'Bali')
    return re.sub(r'（.*?）|\(.*?\)', '', t).strip()

# ---------------------------------------------------------------- audio
async def _tts(text, voice, path, want_bounds):
    import edge_tts
    c = edge_tts.Communicate(text, voice, boundary='WordBoundary')
    b = []; tmp = path + '.part'
    with open(tmp, 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary': b.append([round(ch['offset'] / 10000), ch['text']])
    if os.path.getsize(tmp) < 500: raise RuntimeError('tiny audio ' + path)
    os.replace(tmp, path)
    if want_bounds: json.dump(b, open(path + '.bounds.json', 'w'), ensure_ascii=False)

async def gen_audio(jobs, cache, conc=6, log=print):
    """jobs: list of (acc, key, text, want_bounds). Files cached in cache/acc/key.mp3 (resumable)."""
    sem = asyncio.Semaphore(conc); done = [0]
    todo = [j for j in jobs if not (os.path.exists(os.path.join(cache, j[0], j[1] + '.mp3')) and (not j[3] or os.path.exists(os.path.join(cache, j[0], j[1] + '.mp3.bounds.json'))))]
    log('audio: %d jobs, %d cached, %d to generate' % (len(jobs), len(jobs) - len(todo), len(todo)))
    async def one(j):
        acc, key, text, wb = j; p = os.path.join(cache, acc, key + '.mp3')
        async with sem:
            for attempt in range(5):
                try: await _tts(text, VOICES[acc], p, wb); break
                except Exception as e:
                    if attempt == 4: log('FAIL', acc, key, e); return
                    await asyncio.sleep(2 + attempt * 3)
        done[0] += 1
        if done[0] % 100 == 0: log('  audio %d/%d' % (done[0], len(todo)))
    for a in ('us', 'uk'): os.makedirs(os.path.join(cache, a), exist_ok=True)
    await asyncio.gather(*[one(j) for j in todo])

# ---------------------------------------------------------------- render
def render_chapter(ch, W, bt):
    no = ch['no']; ids = ch['ids']
    occ = {}
    paras = []
    for pi, (en, zh) in enumerate(ch['paras']):
        def rep(m):
            sid = ch['tagmap'][m.group(2)]; k = occ.get(sid, 0); occ[sid] = k + 1; w = W[sid]
            cls = 'tw' + (' st' if w['s'] else '') + ' nwd'
            return '<span class="%s" data-i="%s" id="w%s-%d" tabindex="0">%s<i class="gl">%s</i></span>' % (cls, sid, sid, k, m.group(1), esc(ch['words'][m.group(2)]['gl']))
        body = TAG.sub(rep, html.escape(en, quote=False))
        paras.append('<div class="para" id="c%dp%d"><div class="pen"><button class="say" title="朗读本段" aria-label="朗读本段">▶</button><p class="en" lang="en">%s</p></div><p class="zh" lang="zh">%s</p></div>' % (no, pi, body, esc(zh)))
    stars = sum(1 for i in ids if W[i]['s'])
    rows = []
    for i in ids:
        w = W[i]; z = w['z']; z = z if len(z) <= 60 else z[:58].rstrip('；;，, ') + ' …'
        rows.append('<tr data-i="%s"><td class="wd"><a href="#" class="jump" data-i="%s">%s</a> <sup class="nwt bt">新 %s</sup></td><td class="ph">%s</td><td class="pr"><button class="pw" data-i="%s" data-acc="us" title="美式发音">🇺🇸 美</button><button class="pw" data-i="%s" data-acc="uk" title="英式发音">🇬🇧 英</button></td><td class="mn">%s</td><td class="sr">%s</td><td><label class="lk"><input type="checkbox" class="lrn" data-i="%s"><span>已掌握</span></label></td></tr>' % (i, i, esc(w['w']), esc(bt), esc(w['p']), i, i, esc(z), '★' if w['s'] else '', i))
    # quiz: up to 5 words with short surfaces, spread over chapter
    cand = [i for i in ids if len(W[i]['sf'].split()) <= 3 and W[i]['ss'].count(W[i]['sf']) == 1 and W[i]['sf'] != W[i]['ss']]
    if len(cand) > 5:
        step = len(cand) / 5.0; cand = [cand[int(k * step)] for k in range(5)]
    qs = []
    for i in cand:
        w = W[i]; a = w['sf']; s = w['ss']; x = s.index(a)
        size = len(a) + 1
        first = re.sub(r'[^A-Za-z]', '', a)[:1].lower() or a[:1]
        qs.append('<li data-a="%s" data-i="%s"><span>%s <input type="text" autocomplete="off" autocapitalize="off" spellcheck="false" size="%d" aria-label="填空"> %s</span><em class="hint">提示：%s · 首字母 %s · %d 个字符</em><b class="fb"></b></li>' % (esc(a), i, esc(s[:x]), size, esc(s[x + len(a):]), esc(ch['words'][ch['rev'][i]]['gl']), esc(first), len(a), ))
    quiz = '<div class="quiz"><h3>✍️ 小测：%d 道填空 <small>答案来自本章原句</small></h3><ol>%s</ol><div class="qbtn"><button class="chk">检查答案</button><button class="shw">显示答案</button><button class="rst">重做</button><span class="score"></span></div></div>' % (len(qs), ''.join(qs)) if qs else ''
    return ('<section class="chap" id="c%d" data-c="%d" data-bt="%s">\n' % (no, no, esc(bt)) +
        '<header class="ch-h"><div class="ch-no">Chapter %d<span class="ch-th">%s</span><span class="ch-bt">新 %s</span></div>\n' % (no, esc(ch['theme']), esc(bt)) +
        '<h2><span lang="en">%s</span><small>%s</small></h2>\n' % (esc(ch['title_en']), esc(ch['title_zh'])) +
        '<div class="ch-meta"><span>%d 个词条</span><span>★ %d</span><span class="bt">新 %s · %d</span><span>%d 段</span><span class="ch-prog" data-cp="%d"></span><button class="sayall">▶ 朗读全章</button></div></header>\n' % (len(ids), stars, esc(bt), len(ids), len(ch['paras']), no) +
        '<div class="story">%s</div>\n' % ''.join(paras) +
        '<details class="wl" open><summary>本章词表 <small>%d 词 · 勾选「已掌握」自动保存</small></summary><div class="tblw"><table><thead><tr><th>单词 / 表达</th><th>音标</th><th>发音</th><th>释义</th><th>★</th><th>掌握</th></tr></thead><tbody>%s</tbody></table></div></details>\n' % (len(ids), ''.join(rows)) +
        quiz + '\n</section>\n')

CSS_MARK = '/*bt-css*/'
CSS = CSS_MARK + '.ch-bt,.nwt.bt,.ch-meta span.bt,.pop h4 .bt,.tocbt{background:#e0703a!important;color:#fff!important;border-radius:6px;padding:1px 7px;font-size:11px;font-weight:700;margin-left:8px;letter-spacing:0;text-transform:none;white-space:nowrap;display:inline-block}.ch-meta span.bt{margin-left:0}.tgh.tgbt{color:#e0703a}[data-theme=dark] .ch-bt,[data-theme=dark] .nwt.bt,[data-theme=dark] .ch-meta span.bt,[data-theme=dark] .pop h4 .bt{background:#c4523a!important;color:#fff!important}[data-theme=dark] .tgh.tgbt{color:#f6b26b}'

def patch_stories(s, new_chs, W, CT, total_words, bt_counts):
    for ch in new_chs:
        if 'id="c%d"' % ch['no'] in s: raise SystemExit('chapter %d already in stories.html' % ch['no'])
    secs = ''.join(ch['html'] for ch in new_chs)
    i = s.index('<section class="about"'); s = s[:i] + secs + s[i:]
    # TOC: one group per batch
    by = {}
    for ch in new_chs: by.setdefault(ch['bt'], []).append(ch)
    grp = ''
    for bt, chs in by.items():
        grp += '<div class="tg"><div class="tgh tgbt"><span class="sym">新</span>%s 新增</div>%s</div>' % (esc(bt), ''.join('<a href="#c%d" data-c="%d"><b>%02d</b> %s<small class="np" data-np="%d"></small></a>' % (c['no'], c['no'], c['no'], esc(c['title_zh']), c['no']) for c in chs))
    i = s.index('<div class="tocf">'); s = s[:i] + grp + s[i:]
    # header stats
    nch = len(CT)
    s = re.sub(r'<div><b>\d+</b><span>章</span></div><div><b>\d+</b><span>词条（本书）</span></div>', '<div><b>%d</b><span>章</span></div><div><b>%d</b><span>词条（本书）</span></div>' % (nch, total_words), s, count=1)
    s = re.sub(r'<p class="sub">\d+ 个连续小故事，把单词总表里的 \d+ 个词条', '<p class="sub">%d 个连续小故事，把单词总表里的 %d 个词条' % (nch, total_words), s, count=1)
    if 'id="btstat"' not in s:
        s = s.replace('<div><b id="learnedN">', '<div id="btstat"><b>%s</b><span>最新新增</span></div><div><b id="learnedN">' % esc(' / '.join('%s·%d' % (b, n) for b, n in list(bt_counts.items())[-1:])), 1)
    else:
        s = re.sub(r'<div id="btstat"><b>[^<]*</b>', '<div id="btstat"><b>%s</b>' % esc(' / '.join('%s·%d' % (b, n) for b, n in list(bt_counts.items())[-1:])), s, count=1)
    # about
    li = '<li>%s 更新：新增第 %d–%d 章，覆盖本批 %d 个新词（章节标「新 %s」）。旧章节、旧词条和学习进度不变。</li>' % (new_chs[0]['bt'], new_chs[0]['no'], new_chs[-1]['no'], sum(len(c['ids']) for c in new_chs), new_chs[0]['bt'])
    s = s.replace('<section class="about" id="about"><h2>说明</h2><ul>', '<section class="about" id="about"><h2>说明</h2><ul>' + li, 1)
    # css + popup badge (idempotent)
    if CSS_MARK not in s: s = s.replace('</style>', CSS + '</style>', 1)
    old = "(w.new?'<span class=\"nw\">NEW</span>':'')+'</h4>'"
    if old in s: s = s.replace(old, "(w.new?'<span class=\"nw\">NEW</span>':'')+(w.bt?'<span class=\"bt\">新 '+esc(w.bt)+'</span>':'')+'</h4>'", 1)
    s = re.sub(r'<title>Leo in Bali · 单词故事 v2</title>', '<title>Leo in Bali · 单词故事 v2</title>', s)
    return s

ANKI_MARK = '/*bt-anki*/'
def patch_anki(s, total_words, bts):
    s = re.sub(r'Anki 间隔复习 · \d+ 词', 'Anki 间隔复习 · %d 词' % total_words, s, count=1)
    if ANKI_MARK in s:
        # refresh batch options only
        s = re.sub(r'<select id="fBatch"[^>]*>.*?</select>', batch_select(bts), s, count=1, flags=re.S)
        return s
    s = s.replace('<label><input type="checkbox" id="fNew"> 只看 NEW</label>', '<label><input type="checkbox" id="fNew"> 只看 NEW</label>' + batch_select(bts), 1)
    s = s.replace('<option value="story">按故事章节</option>', '<option value="story">最新新增优先，其余按故事章节</option>', 1)
    # cfg default
    s = s.replace("acc:'us',order:'story'}", "acc:'us',order:'story',bt:''}", 1)
    # filter
    s = s.replace("if(c.nw&&!w.new)return false;return true}", "if(c.nw&&!w.new)return false;if(c.bt&&w.bt!==c.bt)return false;return true}", 1)
    # ordering: batch words (have bt) first, newest class date first; old cards keep their old relative order
    old = "else nw.sort(function(a,b){var A=W[wid(a)],B=W[wid(b)];return (A.h-B.h)||(wid(a)-wid(b))||(a<b?-1:1)});"
    new = "else nw.sort(function(a,b){var A=W[wid(a)],B=W[wid(b)];" + ANKI_MARK + "var bA=A.bt?1:0,bB=B.bt?1:0;if(bA!==bB)return bB-bA;if(bA&&bB&&A.lk!==B.lk)return (B.lk||0)-(A.lk||0);return (A.h-B.h)||(wid(a)-wid(b))||(a<b?-1:1)});"
    assert old in s, 'anki sort anchor not found'
    s = s.replace(old, new, 1)
    # meta badge
    s = s.replace("(w.new?'<span class=\"nw\">NEW</span>':'')+'<span>'", "(w.new?'<span class=\"nw\">NEW</span>':'')+(w.bt?'<span class=\"nw bt\">新 '+esc(w.bt)+' · 课堂 '+esc((w.d||[]).slice(-1)[0]||'')+'</span>':'')+'<span>'", 1)
    # clear filter resets batch too
    s = s.replace("S.cfg.theme='';S.cfg.star=0;S.cfg.nw=0;", "S.cfg.theme='';S.cfg.star=0;S.cfg.nw=0;S.cfg.bt='';if($('#fBatch'))$('#fBatch').value='';", 1)
    s = s.replace("fl=S.cfg.theme||S.cfg.star||S.cfg.nw;", "fl=S.cfg.theme||S.cfg.star||S.cfg.nw||S.cfg.bt;", 1)
    s = s.replace("bind('fNew','nw');", "bind('fNew','nw');bind('fBatch','bt');", 1)
    s = s.replace('</style>', '.nw.bt{background:#e0703a!important;color:#fff!important}[data-theme=dark] .nw.bt{background:#c4523a!important}</style>', 1)
    return s

def batch_select(bts):
    return '<select id="fBatch" aria-label="新增批次"><option value="">全部批次</option>%s</select>' % ''.join('<option value="%s">%s 新增（%d）</option>' % (esc(b), esc(b), n) for b, n in bts.items())

def patch_index(s, nch, total, bt, nbt):
    return re.sub(r'<p>\d+ 章双语故事 · \d+ 个词条（[^）]*）', '<p>%d 章双语故事 · %d 个词条（最新：%s 新增 %d 个）' % (nch, total, bt, nbt), s, count=1)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True); ap.add_argument('--base', required=True, help='当前线上/仓库 site 目录（只读）')
    ap.add_argument('--chapters', default=os.path.join(HERE, 'chapters')); ap.add_argument('--batch', required=True, help='批次标签，如 10/23')
    ap.add_argument('--out', required=True); ap.add_argument('--audio-cache', default=None); ap.add_argument('--no-audio', action='store_true')
    ap.add_argument('--year-start-month', type=int, default=9)
    a = ap.parse_args()
    log = print
    rows = load_csv(a.csv); byid = {r['#']: r for r in rows}
    DATA = json.load(open(os.path.join(a.base, 'data', 'words.json'), encoding='utf-8'))
    W, CH, CT = DATA['W'], DATA['CH'], DATA['CT']
    old_ids = set(W.keys()); old_snapshot = json.dumps({k: W[k] for k in sorted(old_ids, key=int)}, ensure_ascii=False, sort_keys=True)
    new, changed, removed = diff(rows, W)
    log('diff: master %d rows | new %d | changed %d | removed %d' % (len(rows), len(new), len(changed), len(removed)))
    newn = {norm(r['单词']): r for r in new}
    # chapters not yet in base
    base_st = open(os.path.join(a.base, 'stories.html'), encoding='utf-8').read()
    chs = []
    for fn in sorted(os.listdir(a.chapters)):
        if not re.match(r'ch\d+\.txt$', fn): continue
        ch = parse_chapter(os.path.join(a.chapters, fn))
        if 'id="c%d"' % ch['no'] in base_st or str(ch['no']) in CT: continue
        chs.append(ch)
    chs.sort(key=lambda c: c['no'])
    # id assignment (stable: continues after max id), CSV order
    nid = max(int(k) for k in W) + 1
    covered = {}
    for ch in chs:
        for cid in ch['words']:
            r = byid.get(cid)
            if not r or norm(r['单词']) not in newn: raise SystemExit('ch%d: tag id %s is not a new word in this CSV' % (ch['no'], cid))
            covered[cid] = ch['no']
    need_story = [r for r in new if r['#'] not in covered]
    sid_of = {}
    for r in sorted([r for r in new if r['#'] in covered], key=lambda r: int(r['#'])):
        sid_of[r['#']] = str(nid); nid += 1
    # build W entries
    bt = a.batch
    for ch in chs:
        ch['bt'] = bt; ch['tagmap'] = {c: sid_of[c] for c in ch['words']}; ch['rev'] = {v: k for k, v in ch['tagmap'].items()}
        order = []
        for en, zh in ch['paras']:
            for m in TAG.finditer(en):
                if m.group(2) not in order: order.append(m.group(2))
        ch['ids'] = [sid_of[c] for c in order]
        for c in order:
            r = byid[c]; wd = ch['words'][c]; sid = sid_of[c]
            # first occurrence sentence
            ss = sf = ''
            for en, zh in ch['paras']:
                m = re.search(r'\{([^{}|]+)\|%s\}' % c, en)
                if m:
                    sf = m.group(1); txt = plain(en)
                    for snt in sentences(txt):
                        if sf in snt: ss = snt; break
                    break
            dates = [d.strip() for d in r['出现日期'].split(' / ') if d.strip()]
            cnt = sum(len(re.findall(r'\{[^{}|]+\|%s\}' % c, en)) for en, zh in ch['paras'])
            W[sid] = {'w': clean(r['单词']), 'p': r['音标'] or wd['p'], 'z': r['中文'], 't': [r['主题']], 's': 1 if r['高频'] else 0,
                      'g': r['笔记线索'], 'n': int(r['出现次数'] or 0), 'd': dates, 'b': r['来源'], 'k': wd['k'], 'x': wd['x'][:3],
                      'new': 0, 'h': ch['no'], 'ss': ss, 'sf': sf, 'sh': ch['no'], 'c': cnt,
                      'bt': bt, 'ld': dates[-1] if dates else '', 'lk': date_key(dates[-1], a.year_start_month) if dates else 0, 'cid': r['#']}
        CH[str(ch['no'])] = ch['ids']; CT[str(ch['no'])] = ch['title_zh']
    # prove old untouched
    assert json.dumps({k: W[k] for k in sorted(old_ids, key=int)}, ensure_ascii=False, sort_keys=True) == old_snapshot
    for ch in chs: ch['html'] = render_chapter(ch, W, bt)
    # ---- output tree
    out_site = os.path.join(a.out, 'site'); dep = os.path.join(a.out, 'deploy')
    if os.path.exists(out_site): shutil.rmtree(out_site)
    shutil.copytree(a.base, out_site)
    if os.path.exists(dep): shutil.rmtree(dep)
    os.makedirs(os.path.join(dep, 'data'), exist_ok=True)
    changed_files = []
    def write(rel, content):
        p = os.path.join(out_site, rel); tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8').write(content); os.replace(tmp, p)
        d = os.path.join(dep, rel); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(p, d); changed_files.append(rel)
    total = len(W)
    bts = {}
    for k, v in W.items():
        if v.get('bt'): bts[v['bt']] = bts.get(v['bt'], 0) + 1
    # audio
    cache = a.audio_cache or os.path.join(a.out, 'audio_cache')
    jobs = []
    for ch in chs:
        for pi, (en, zh) in enumerate(ch['paras']):
            for acc in VOICES: jobs.append((acc, 'c%dp%d' % (ch['no'], pi), plain(en), True))
        for sid in ch['ids']:
            w = W[sid]
            for acc in VOICES:
                jobs.append((acc, 'w' + sid, tts_word_text(w['w']), False))
                for j, x in enumerate(w['x']): jobs.append((acc, 'x%s_%d' % (sid, j), x[0], False))
    BOUNDS = read_js_var(os.path.join(a.base, 'data', 'bounds.js'), 'BOUNDS')
    if not a.no_audio:
        asyncio.run(gen_audio(jobs, cache, log=log))
    missing = []
    for acc, key, text, wb in jobs:
        src = os.path.join(cache, acc, key + '.mp3')
        if not os.path.exists(src): missing.append((acc, key)); continue
        dst = os.path.join(out_site, 'audio', acc, key + '.mp3')
        if os.path.exists(os.path.join(a.base, 'audio', acc, key + '.mp3')): raise SystemExit('refusing to overwrite existing audio ' + key)
        shutil.copy2(src, dst); os.makedirs(os.path.join(dep, 'audio', acc), exist_ok=True); shutil.copy2(src, os.path.join(dep, 'audio', acc, key + '.mp3'))
        if wb: BOUNDS[acc][key] = json.load(open(src + '.bounds.json'))
    # data
    js = json.dumps(DATA, ensure_ascii=False, separators=(',', ':'))
    write('data/words.json', js); write('data/words.js', 'var DATA=' + js + ';')
    write('data/bounds.js', 'var BOUNDS=' + json.dumps(BOUNDS, ensure_ascii=False, separators=(',', ':')) + ';')
    st = patch_stories(base_st, chs, W, CT, total, bts) if chs else base_st
    write('stories.html', st)
    write('anki.html', patch_anki(open(os.path.join(a.base, 'anki.html'), encoding='utf-8').read(), total, bts))
    write('index.html', patch_index(open(os.path.join(a.base, 'index.html'), encoding='utf-8').read(), len(CT), total, bt, bts.get(bt, 0)))
    # report
    rep = {'time': datetime.datetime.now().isoformat(timespec='seconds'), 'batch': bt, 'master_rows': len(rows), 'base_words': len(old_ids),
           'new': len(new), 'added_with_story': len(sid_of), 'need_story': [{'#': r['#'], 'w': r['单词'], '主题': r['主题']} for r in need_story],
           'changed': changed, 'removed': removed, 'new_chapters': [{'no': c['no'], 'title_en': c['title_en'], 'title_zh': c['title_zh'], 'words': len(c['ids'])} for c in chs],
           'total_words': total, 'audio_jobs': len(jobs), 'audio_missing': missing, 'deploy_files': len(changed_files) + len(jobs) - len(missing),
           'id_map': {r_: sid_of[r_] for r_ in sid_of}}
    json.dump(rep, open(os.path.join(a.out, 'update_report.json'), 'w'), ensure_ascii=False, indent=1)
    if need_story:
        with open(os.path.join(a.out, 'need_story_TODO.txt'), 'w', encoding='utf-8') as f:
            f.write('# 这些新词还没有故事章节，请按 chapters/chNN.txt 格式补写后重跑\n')
            for r in need_story: f.write('%s | %s | %s | %s | %s\n' % (r['#'], r['单词'], r['中文'], r['主题'], r['出现日期']))
    log('new chapters:', [c['no'] for c in chs], '| words added:', len(sid_of), '| need story:', len(need_story), '| audio missing:', len(missing))
    log('out:', out_site, '| deploy:', dep)

if __name__ == '__main__':
    main()
