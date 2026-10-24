#!/usr/bin/env python3
"""缓存修复（幂等）：给 html 里的 data/words.js、data/bounds.js 引用加 ?v=<文件内容哈希前8位>，
文件内容一变版本号自动变，手机/App 内置浏览器不会再用旧数据；并让「已掌握」只统计当前 W 里还存在的词。
用法：python3 build/cachefix.py SITE_DIR"""
import sys, os, re, hashlib
site = sys.argv[1]
def ver(rel): return hashlib.md5(open(os.path.join(site, rel), 'rb').read()).hexdigest()[:8]
V = {r: ver(r) for r in ('data/words.js', 'data/bounds.js')}
for f in ('stories.html', 'anki.html', 'index.html'):
    p = os.path.join(site, f); s = open(p, encoding='utf-8').read(); o = s
    for r, v in V.items():
        s = re.sub(r'src="%s(\?v=[0-9a-f]+)?"' % re.escape(r), 'src="%s?v=%s"' % (r, v), s)
    if f == 'stories.html':
        s = s.replace("Object.keys(learned).forEach(function(k){if(learned[k])tot++})", "Object.keys(learned).forEach(function(k){if(learned[k]&&W[k])tot++})")
    if s != o: open(p, 'w', encoding='utf-8').write(s); print('patched', f)
print('versions', V)
