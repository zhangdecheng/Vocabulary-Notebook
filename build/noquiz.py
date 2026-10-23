#!/usr/bin/env python3
"""去掉故事页里多余的「填空小测」和「说明」（幂等）。用法：python3 build/noquiz.py SITE_DIR
- 每章末尾的 <div class="quiz">…</div>（✍️ 小测：N 道填空 + 提示 + 检查/显示/重做按钮）
- 章节列表最后的「说明」区 <section class="about" id="about">…</section>，以及目录底部指向它的「说明」链接
- 用法提示里的「做填空小测」
章节正文、词表、弹窗、音频、导航都不动。update.py 的 render_chapter 已不再生成小测，这里负责清理旧章节。"""
import sys, os, re
S = os.path.join(sys.argv[1], 'stories.html'); s = open(S, encoding='utf-8').read(); n0 = len(s)
s, nq = re.subn(r'<div class="quiz"><h3>.*?<span class="score"></span></div></div>', '', s, flags=re.S)
s, na = re.subn(r'<section class="about" id="about">.*?</section>\n?', '', s, flags=re.S)
s = s.replace('<div class="tocf"><a href="#about">说明</a></div>', '<div class="tocf"></div>')
s = s.replace('读完一章勾选词表、做填空小测。', '读完一章在词表里勾「已掌握」。')
s = re.sub(r'/\*noquiz\*/.*?/\*/noquiz\*/', '', s, flags=re.S)
s = s.replace('</style>', '/*noquiz*/.tocf:empty{display:none}/*/noquiz*/</style>', 1)
assert 'class="quiz"' not in s and 'id="about"' not in s and '做填空小测' not in s
open(S + '.tmp', 'w', encoding='utf-8').write(s); os.replace(S + '.tmp', S)
print('noquiz: removed %d quizzes, %d about section(s), %d bytes' % (nq, na, n0 - len(s)))
