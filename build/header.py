#!/usr/bin/env python3
"""v2 柔和配色 + 故事页头部改版（Iris 规范 v2，张总 10/24 确认）。幂等，可重复运行。
用法：python3 build/header.py SITE_DIR      （在 navfix.py 之后、cachefix.py 之前/之后均可）
- 三个页面（index / stories / anki）追加同一套 v2 配色变量与组件覆盖样式（<!--v2pal--> 块）；
- stories.html：头部换成 标题行 / 继续阅读 / 最新补充 / 已掌握 / 次按钮；工具条只留 搜索+⚙ 和 显示模式；其余控件进设置面板；
- 数字（章数、词数、最新批次、章节范围）运行时从 DATA 计算，HTML 里的静态值由本脚本按 words.json 刷新；
- 不改任何 section.chap、词数据、音频、Anki 卡片和进度键值；新增键只有 wsx-last（navfix）。"""
import sys, os, re, json, datetime
SITE = sys.argv[1]
def rd(f): return open(os.path.join(SITE, f), encoding='utf-8').read()
def wr(f, s): open(os.path.join(SITE, f), 'w', encoding='utf-8').write(s)

D = json.load(open(os.path.join(SITE, 'data', 'words.json'), encoding='utf-8'))
W, CH, CT = D['W'], D['CH'], D['CT']
NCH, NW = len(CH), len(W)
NNEW = sum(1 for v in W.values() if v.get('new'))

PAL = r'''<!--v2pal--><style id="v2pal">
/* v2 柔和配色（Iris 规范 §6）。--hl/--hlb/--star 与 Anki 评分按钮本轮不改 */
:root,html[data-theme=light]{--bg:#efe9df;--hdr:linear-gradient(180deg,#e7dfd3 0%,#ebe4d9 100%);--card:#f6f1e9;--card2:#ebe3d7;--ink:#2e2a25;--mut:#665d53;--line:#ddd3c5;--bd:#85796b;
--acc:#9a5b3e;--on-acc:#f6f1e9;--acc-t:#8c4f33;--acc2:#437066;--track:#d9cfc1;--nwd:#5f8c82;--pill-bg:#ebe3d7;--pill-ink:#8c4f33;--new-bg:#ebe3d7;--new-ink:#8c4f33;
--bar:rgba(239,233,223,.96);--dim:rgba(46,42,37,.40);--shadow:0 2px 8px rgba(80,60,40,.10);--seg-on:#9a5b3e;--seg-on-ink:#f6f1e9;--zh:#5c5249;--tint:#e3ebe7}
html[data-theme=dark]{--bg:#1f1d1a;--hdr:linear-gradient(180deg,#26231f 0%,#221f1c 100%);--card:#282522;--card2:#302c28;--ink:#e8e1d6;--mut:#a59d92;--line:#3a3631;--bd:#7a7064;
--acc:#c58a6b;--on-acc:#1f1d1a;--acc-t:#d29b7d;--acc2:#86b3a8;--track:#3d3833;--nwd:#86b3a8;--pill-bg:#302c28;--pill-ink:#d9b49c;--new-bg:#302c28;--new-ink:#ddb092;
--bar:rgba(31,29,26,.96);--dim:rgba(0,0,0,.55);--shadow:0 2px 10px rgba(0,0,0,.25);--seg-on:#c58a6b;--seg-on-ink:#1f1d1a;--zh:#c2b9ad;--tint:#26302d}
html[data-theme] body{background:var(--bg);color:var(--ink)}
html[data-theme] .seg,html[data-theme] .icon,html[data-theme] select,html[data-theme] #q,html[data-theme] .qr,html[data-theme] .say,html[data-theme] .pop,html[data-theme] .pop .row button,html[data-theme] .pw,html[data-theme] #totop,html[data-theme] .pop .px,html[data-theme] input[type=number],html[data-theme] .btn,html[data-theme] .sx .px,html[data-theme] details.set,html[data-theme] kbd,html[data-theme] .quiz input{background:var(--card);color:var(--ink);border-color:var(--bd)}
html[data-theme] .seg button+button{border-left-color:var(--bd)}
html[data-theme] .seg button.on,html[data-theme] .seg.acc button.on,html[data-theme] .btn.pri{background:var(--seg-on);color:var(--seg-on-ink);border-color:var(--seg-on)}
html[data-theme] .say{color:var(--acc2);border-color:var(--line)}
html[data-theme] .sayall{background:var(--card);color:var(--acc2);border-color:var(--acc2)}
html[data-theme] .say:hover,html[data-theme] .say.on{background:var(--acc2);color:var(--on-acc);border-color:var(--acc2)}
html[data-theme] .qbtn button{background:var(--acc2);color:var(--on-acc)}
html[data-theme] .qbtn .shw,html[data-theme] .qbtn .rst{background:var(--card);color:var(--acc2);border:1px solid var(--acc2)}
html[data-theme] .pw.cur{border-color:var(--acc2);color:var(--acc2)}html[data-theme] .pw:hover{background:var(--tint)}
html[data-theme] .qr a{border-color:var(--line)}
html[data-theme] .tgh,html[data-theme] .pop .form,html[data-theme] .toc a b,html[data-theme] .ch-no,html[data-theme] .cast b,html[data-theme] .pop .co b,html[data-theme] .pop .sc>b,html[data-theme] .box h4,html[data-theme] .co b,html[data-theme] td.wd a{color:var(--acc-t)}
html[data-theme] td.wd a{color:var(--ink);border-bottom-color:var(--acc-t)}
html[data-theme] .toc{background:var(--card);border-color:var(--line)}
html[data-theme] .toc a:hover,html[data-theme] .toc a.cur{background:var(--card2)}
html[data-theme] .cast div,html[data-theme] .pop .nt,html[data-theme] .skipbox,html[data-theme] .box,html[data-theme] .nt{background:var(--card2);color:var(--ink)}
html[data-theme] .ch-meta span{background:var(--card2)}html[data-theme] .ch-meta .ch-prog{background:var(--tint);color:var(--acc2)}
html[data-theme] .intro,html[data-theme] .chap,html[data-theme] .about{background:var(--card);border-color:var(--line);box-shadow:var(--shadow)}
html[data-theme] .para.reading{background:var(--tint);box-shadow:inset 3px 0 0 var(--acc2)}
html[data-theme] .zh{color:var(--zh);border-left-color:var(--line)}
html[data-theme] .tw.nwd{box-shadow:none}
html[data-theme] .tw.nwb{box-shadow:inset 0 -2px 0 var(--nwd)}
html[data-theme] .pop{box-shadow:0 18px 40px rgba(60,45,30,.18);border-color:var(--line)}html[data-theme=dark] .pop{box-shadow:0 18px 40px rgba(0,0,0,.55)}
html[data-theme] .pop .co,html[data-theme] .co{color:var(--ink)}
html[data-theme] .pop .sx,html[data-theme] .sx{background:var(--tint);border-color:var(--line)}
html[data-theme] .wl{background:var(--bg);border-color:var(--line)}
html[data-theme] th{background:var(--card2)}html[data-theme] td{border-color:var(--line)}
html[data-theme] tr.done td{background:var(--tint)}html[data-theme] .g-test td.mn{background:var(--card2)}
html[data-theme] .quiz{background:var(--tint);border-color:var(--line)}
html[data-theme] .toast{background:var(--ink);color:var(--bg)}
html[data-theme] .nwt,html[data-theme] .pop h4 .nw,html[data-theme] .meta .nw,html[data-theme] .lacc{background:var(--acc2);color:var(--on-acc)}
html[data-theme] .ch-bt,html[data-theme] .nwt.bt,html[data-theme] .ch-meta span.bt,html[data-theme] .pop h4 .bt,html[data-theme] .tocbt,html[data-theme] .nw.bt{background:var(--new-bg)!important;color:var(--new-ink)!important;box-shadow:inset 0 0 0 1px var(--line)}
html[data-theme] .tgh.tgbt{color:var(--acc-t)}
html[data-theme] #menu{background:var(--acc);color:var(--on-acc);box-shadow:var(--shadow)}
html[data-theme] .card,html[data-theme] a.c{background:var(--card);border-color:var(--line);box-shadow:var(--shadow)}
html[data-theme] .meta .tag,html[data-theme] .stat div{background:var(--card2)}
html[data-theme] .show{background:var(--ink);color:var(--bg)}
html[data-theme] a.c p,html[data-theme] .f{color:var(--mut)}
/* index / anki 头部：平静的表面，不再用饱和渐变 */
html[data-theme] .top{background:var(--hdr);color:var(--ink);border-bottom:1px solid var(--line)}
html[data-theme] .top a{color:var(--acc-t)}
html[data-theme] .top .cnt span{background:var(--card2);color:var(--ink)}
html[data-theme] .top .cnt .n b{color:var(--acc2)}html[data-theme] .top .cnt .l b{color:var(--acc-t)}html[data-theme] .top .cnt .r b{color:var(--ink)}
html[data-theme] #thm{background:var(--card);color:var(--ink);border:1px solid var(--bd)}
html[data-theme] #thm:hover{background:var(--card2)}
@media print{html[data-theme] .top{background:none}}
</style><!--/v2pal-->'''

HCSS = r'''<!--v2hdr-css--><style id="v2hdr-css">
html{scroll-padding-top:80px}
.hero{background:var(--bg)}
.hd{background:var(--hdr);border-bottom:1px solid var(--line);padding:12px 16px 14px;color:var(--ink)}
.hd .trow{display:flex;align-items:center;gap:8px;min-height:44px}
.hd .trow h1{margin:0;font-family:var(--serif);font-size:24px;line-height:1.2;font-weight:700;white-space:nowrap;color:var(--ink);letter-spacing:0}
html[data-theme] .hd .lvl{margin:0;background:var(--pill-bg);color:var(--pill-ink);font-weight:700;font-size:13px;line-height:1;border-radius:999px;padding:6px 10px;white-space:nowrap;border:1px solid var(--line);box-shadow:none}
html[data-theme] .hd #thm{position:static;margin-left:auto;width:44px;height:44px;border-radius:50%;padding:0;display:grid;place-items:center;font-size:18px;flex:none;line-height:1}
html[data-theme] .hd .sub{margin:2px 0 0;font-size:14px;color:var(--mut);opacity:1}
.act{padding:16px;display:flex;flex-direction:column;gap:12px}
.cont{display:flex;align-items:center;gap:12px;width:100%;min-height:64px;border:0;border-radius:16px;background:var(--acc);color:var(--on-acc);padding:10px 16px;text-align:left;box-shadow:var(--shadow);cursor:pointer;font:inherit}
.cont .ic{font-size:13px;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;border:2px solid currentColor;flex:none;padding-left:2px}
.cont .tx{flex:1;min-width:0}.cont b{display:block;font-size:17px;line-height:1.3;padding-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.cont small{display:block;font-size:12.5px;line-height:1.3;opacity:.92}.cont .chev{font-size:22px;flex:none}
.hero .hc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;color:var(--ink);box-shadow:none}
.newc{display:flex;align-items:center;gap:12px;min-height:72px;text-decoration:none}
.newc[hidden]{display:none}
.newc .k{font-size:13px;color:var(--mut);display:flex;align-items:center;gap:6px}
.newc .bt{background:var(--new-bg);color:var(--new-ink);font-weight:700;font-size:12px;border-radius:6px;padding:2px 7px;box-shadow:inset 0 0 0 1px var(--line)}
.newc .v{display:block;font-size:16px;margin-top:2px}.newc .v b{font-size:20px;color:var(--new-ink);margin-right:6px}
.newc .go{margin-left:auto;color:var(--acc-t);font-weight:600;font-size:15px;white-space:nowrap;min-height:44px;display:flex;align-items:center}
.prog .h{display:flex;align-items:baseline;gap:8px}.prog .h>span{font-size:13px;color:var(--mut)}
.prog .h b{font-size:18px}.prog .h b em{font-style:normal;font-weight:500;color:var(--mut);font-size:15px}
.prog .pct{margin-left:auto;font-weight:700;color:var(--acc2)!important;font-size:15px!important;white-space:nowrap}
.prog .pct.tip0{font-weight:400;color:var(--mut)!important;font-size:13px!important;white-space:normal;text-align:right}
.prog .trk{height:6px;border-radius:3px;background:var(--track);margin-top:8px;overflow:hidden}.prog .trk i{display:block;height:100%;width:0;background:var(--acc2);border-radius:3px;transition:width .3s}
.prog .pn{font-size:12px;color:var(--mut);margin-top:6px}
.sec{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.sec a{min-height:44px;border-radius:12px;border:1px solid var(--bd);display:flex;align-items:center;justify-content:center;color:var(--ink);text-decoration:none;font-size:15px}
.sec a:hover{background:var(--card2)}
.tools{display:contents}
.tb{position:sticky;top:0;z-index:30;background:var(--bar);border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:8px 16px;display:flex;gap:8px;align-items:center;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
html[data-theme] .tb .search{position:relative;flex:1;min-width:0;max-width:none;margin:0;order:0}
.tb .search::before{content:"🔍";position:absolute;left:14px;top:50%;transform:translateY(-50%);font-size:15px;pointer-events:none;opacity:.8}
html[data-theme] .tb #q{height:44px;border:1px solid var(--bd);border-radius:999px;background:var(--card);padding:0 14px 0 40px;font-size:15px}
.gear{width:44px;height:44px;border-radius:50%;border:1px solid var(--bd);background:var(--card);color:var(--ink);font-size:19px;display:grid;place-items:center;flex:none;cursor:pointer;padding:0;line-height:1}
.gear:hover{background:var(--card2)}
.modes{padding:10px 16px 12px}
html[data-theme] .modes .seg,html[data-theme] #sheet .seg{display:flex;width:100%;border:1px solid var(--bd);border-radius:12px;overflow:hidden;background:var(--card)}
html[data-theme] .modes .seg button,html[data-theme] #sheet .seg button{flex:1;min-height:44px;font-size:15px;padding:0 6px;white-space:nowrap}
html[data-theme] .modes .seg button.on,html[data-theme] #sheet .seg button.on{font-weight:600}
#sdim{position:fixed;inset:0;background:var(--dim);z-index:70}
#sheet{position:fixed;left:0;right:0;bottom:0;z-index:71;background:var(--card);color:var(--ink);border-radius:20px 20px 0 0;padding:8px 16px calc(20px + env(safe-area-inset-bottom));max-height:88vh;overflow:auto;box-shadow:0 -8px 24px rgba(0,0,0,.25);overscroll-behavior:contain}
#sheet[hidden],#sdim[hidden]{display:none}
#sheet .grab{width:40px;height:5px;border-radius:3px;background:var(--bd);margin:2px auto 4px}
#sheet .shh{display:flex;align-items:center;min-height:44px}#sheet .shh h3{margin:0;font-size:18px}
#sheet .sx{margin-left:auto;width:44px;height:44px;border:0;background:none;font-size:22px;color:var(--mut);cursor:pointer;padding:0}
#sheet .gt{font-size:13px;font-weight:700;color:var(--acc-t);letter-spacing:.5px;margin:12px 0 6px}
#sheet .srow{margin-bottom:12px}#sheet .slb{font-size:14px;color:var(--mut);margin-bottom:6px;display:flex;justify-content:space-between}
#sheet .shint{font-size:12.5px;color:var(--mut);margin-top:6px}
#sheet .step{display:flex;align-items:center;gap:10px}#sheet .step button{width:56px;height:44px;border-radius:12px;border:1px solid var(--bd);background:var(--card);color:var(--ink);font-size:16px;cursor:pointer}
#sheet .step .val{flex:1;text-align:center;font-size:16px}
#sheet .stopb{width:100%;min-height:44px;border-radius:12px;border:1px solid var(--bd);background:transparent;color:var(--ink);font-size:15px;cursor:pointer}
#sheet .sgl{height:1px;background:var(--line);margin:4px 0}
body.sheet-open{overflow:hidden}
@media (max-width:900px){html{scroll-padding-top:72px}}
@media (min-width:901px){
 #sheet{left:auto;right:auto;bottom:auto;width:360px;border-radius:16px;max-height:calc(100vh - 100px);padding:8px 16px 16px;box-shadow:0 18px 40px rgba(0,0,0,.28);border:1px solid var(--line)}
 #sheet .grab{display:none}#sdim{background:transparent}
 .toc{top:84px;max-height:calc(100vh - 100px)}
}
@media (min-width:1024px){
 .hero{display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-areas:"top top cont" "new prog sec";gap:16px 20px;padding:20px max(24px,calc((100% - 1232px)/2));background:var(--hdr);border-bottom:1px solid var(--line)}
 .hd{grid-area:top;padding:0;align-self:center;background:none;border:0}
 .hd .trow h1{font-size:30px}html[data-theme] .hd .sub{font-size:15px}
 html[data-theme] .hd #thm{margin-left:16px}
 .act{display:contents}.cont{grid-area:cont;align-self:center}.newc{grid-area:new}.prog{grid-area:prog;display:flex;flex-direction:column;justify-content:center}
 .sec{grid-area:sec;grid-template-columns:1fr;gap:8px}
 .tools{display:flex;position:sticky;top:0;z-index:30;background:var(--bar);border-bottom:1px solid var(--line);padding:10px max(24px,calc((100% - 1232px)/2));gap:16px;align-items:center;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
 .tb{position:static;border:0;padding:0;background:none;flex:0 1 460px;order:2;margin-left:auto;-webkit-backdrop-filter:none;backdrop-filter:none}
 .modes{padding:0;flex:0 0 420px}
}
@media print{.act,.tools,#sheet,#sdim,.hd #thm{display:none!important}.hd{background:none;border-bottom:2px solid #000}}
</style><!--/v2hdr-css-->'''

HERO = '''<div class="hero" id="hero">
<header class="hd"><div class="trow"><h1>Leo in Bali</h1><span class="lvl">A2–B1</span><!--thm--><button id="thm" type="button" aria-label="切换夜间/日间模式" title="切换夜间/日间模式"></button><!--/thm--></div><p class="sub"><span data-x="ch">{NCH}</span> 章 · <span data-x="w">{NW}</span> 词</p><button id="menu" class="icon" aria-label="目录">☰</button></header>
<section class="act" aria-label="快速入口">
<button class="cont" id="cont" type="button"><span class="ic" aria-hidden="true">▶</span><span class="tx"><b id="contT">从第 1 章开始</b><small id="contS">{CT1}</small></span><span class="chev" aria-hidden="true">›</span></button>
<a class="hc newc" id="newc" href="#c{NF}"><span><span class="k">最新补充 <span class="bt" data-x="lbt">新 {LB}</span></span><span class="v"><b data-x="lbn">+{LBN} 词</b><span data-x="lbr">第 {NF}–{NL} 章（{NC} 章）</span></span></span><span class="go">去看 ›</span></a>
<div class="hc prog" id="prog"><div class="h"><span>已掌握</span><b><span id="learnedN">0</span> <em>/ <span data-x="w">{NW}</span></em></b><span class="pct" id="learnedP"></span></div><div class="trk"><i id="learnedBar"></i></div><div class="pn">含 Anki 熟练词（复习间隔 ≥21 天）</div></div>
<nav class="sec" aria-label="其他页面"><a href="index.html">← 首页</a><a href="anki.html">🗂 Anki 复习</a></nav>
</section></div>'''

TOOLS = '''<div class="tools" id="toolbar">
<div class="tb"><div class="search"><input id="q" type="search" placeholder="搜索单词或中文释义…" autocomplete="off" aria-label="搜索单词或中文释义"><div id="qr" class="qr"></div></div><button id="gear" class="gear" type="button" aria-label="设置" aria-haspopup="dialog" aria-controls="sheet">⚙︎</button></div>
<div class="modes"><div class="seg" data-k="mode"><button data-v="both" class="on">中英对照</button><button data-v="en">只看英文</button><button data-v="zh">只看中文</button></div></div>
</div>
<div id="sdim" hidden></div>
<div id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetH" hidden>
<div class="grab"></div>
<div class="shh"><h3 id="sheetH">设置</h3><button class="sx" id="sheetX" type="button" aria-label="关闭设置">✕</button></div>
<div class="gt">阅读</div>
<div class="srow"><div class="slb">释义方式</div><div class="seg" data-k="gloss"><button data-v="pop" class="on">点词看释义</button><button data-v="inline">行内释义</button><button data-v="test">自测</button></div><div class="shint">自测：隐藏中文和释义，点一下才显示</div></div>
<div class="srow"><div class="slb">字号<span>14–28</span></div><div class="step"><button id="fsm" type="button" aria-label="字号减小">A−</button><span class="val" id="fsv">18 px</span><button id="fsp" type="button" aria-label="字号增大">A+</button></div></div>
<div class="sgl"></div>
<div class="gt">发音</div>
<div class="srow"><div class="slb">口音</div><div class="seg acc" id="accsw"><button data-v="us">🇺🇸 美式</button><button data-v="uk">🇬🇧 英式</button></div></div>
<div class="srow"><div class="slb">语速</div><div class="seg" data-k="rate" id="rateseg"><button data-v="0.75">0.75×</button><button data-v="0.9">0.9×</button><button data-v="1" class="on">1.0×</button><button data-v="1.25">1.25×</button></div><select id="rate" hidden aria-hidden="true"><option value="0.75">0.75×</option><option value="0.9">0.9×</option><option value="1" selected>1.0×</option><option value="1.25">1.25×</option></select></div>
<div class="srow"><button class="stopb" id="stop" type="button">■ 停止朗读</button><div class="shint">停止当前正在播放的段落 / 全章朗读</div></div>
</div>'''

HJS = r'''<!--v2hdr--><script>(function(){
var $=function(q,r){return (r||document).querySelector(q)},$$=function(q,r){return Array.prototype.slice.call((r||document).querySelectorAll(q))};
var W=DATA.W,CHD=DATA.CH,CT=DATA.CT,body=document.body;function nav(){return window.__nav||null}
function ls(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
var ids=Object.keys(W),NWD=ids.length,chs=Object.keys(CHD).map(Number).sort(function(a,b){return a-b});
// ---- 最新批次：文档里最后一个带 data-bt 的章节所属批次
var secs=$$('section.chap'),LB='';secs.forEach(function(s){var b=s.getAttribute('data-bt');if(b)LB=b});
var lbSecs=secs.filter(function(s){return s.getAttribute('data-bt')===LB}).map(function(s){return +s.getAttribute('data-c')});
var lbN=ids.filter(function(i){return LB&&W[i].bt===LB}).length;
function batchDate(bt,now){var m=/^(\d{1,2})\/(\d{1,2})$/.exec(bt||'');if(!m)return null;now=now||new Date();var d=new Date(now.getFullYear(),+m[1]-1,+m[2]);if(d-now>86400000)d=new Date(now.getFullYear()-1,+m[1]-1,+m[2]);return d}
function batchVisible(now){now=now||new Date();var d=batchDate(LB,now);return !!(d&&lbN>0&&(now-d)<30*86400000)}
function setX(k,v){$$('[data-x="'+k+'"]').forEach(function(e){e.textContent=v})}
setX('ch',chs.length);setX('w',NWD);setX('nw',ids.filter(function(i){return W[i].new}).length);
if(LB&&lbSecs.length){setX('lbt','新 '+LB);setX('lb',LB);setX('lbn','+'+lbN+' 词');setX('lbnn',lbN);setX('lbr','第 '+lbSecs[0]+'–'+lbSecs[lbSecs.length-1]+' 章（'+lbSecs.length+' 章）');setX('lbr2',lbSecs[0]+'–'+lbSecs[lbSecs.length-1])}
var newc=$('#newc');if(newc){newc.hidden=!batchVisible();if(lbSecs.length)newc.setAttribute('href','#c'+lbSecs[0]);
  newc.addEventListener('click',function(e){if(nav()&&lbSecs.length){e.preventDefault();nav().go(lbSecs[0])}})}
// ---- 绿色下划线只标最新一批（不改章节 HTML）
$$('.tw[data-i]').forEach(function(t){var w=W[t.getAttribute('data-i')];t.classList.toggle('nwb',!!(LB&&w&&w.bt===LB))});
$$('.intro .tw.demo.nwb').forEach(function(t){t.classList.add('nwb')});
// ---- 继续阅读
var cont=$('#cont');
function lastRec(){var L=nav()&&nav().last?nav().last():ls('wsx-last');return L&&CT[L.c]?L:null}
function paintCont(){if(!cont)return;var L=lastRec();
  if(!L){$('#contT').textContent='从第 '+chs[0]+' 章开始';$('#contS').textContent=CT[chs[0]]||'';cont.setAttribute('data-c',chs[0]);cont.setAttribute('data-p','');return}
  var pm=/p(\d+)$/.exec(L.p||'');
  $('#contT').textContent='继续阅读 · 第 '+L.c+' 章《'+CT[L.c]+'》';
  $('#contS').textContent=pm?'上次读到第 '+(+pm[1]+1)+' 段':'从本章开头读';
  cont.setAttribute('data-c',L.c);cont.setAttribute('data-p',L.p||'')}
if(cont)cont.addEventListener('click',function(){var c=+cont.getAttribute('data-c'),p=cont.getAttribute('data-p')||'';
  if(nav())nav().go(c,p);else location.hash=p||('c'+c)});
paintCont();
var hero=$('#hero'),tk=0;window.addEventListener('scroll',function(){if(tk)return;tk=requestAnimationFrame(function(){tk=0;if(hero&&hero.getBoundingClientRect().bottom>0)paintCont()})},{passive:true});
// ---- 已掌握 = 勾选 ∪ Anki 熟练（q==='r' 且 iv>=21，正向/反向任一张），按词去重，只数当前 W 里的词；只读 wsv2-anki
function ok(c){return !!(c&&c.q==='r'&&c.iv>=21)}
function mast(){var L=ls('wsx-learned')||{},A=ls('wsv2-anki'),cards=(A&&A.cards)||{},n=0;
  for(var k=0;k<NWD;k++){var i=ids[k];if(L[i]||ok(cards[i])||ok(cards['r'+i]))n++}
  var e=$('#learnedN'),p=$('#learnedP'),bar=$('#learnedBar');if(!e)return n;e.textContent=n;
  var r=NWD?n/NWD:0;bar.style.width=(r*100).toFixed(2)+'%';
  p.classList.toggle('tip0',n===0);
  p.textContent=n===0?'读完一章，在词表里勾「已掌握」':(n===NWD?'100% ✓':(r<0.01?'<1%':Math.min(99,Math.floor(r*100))+'%'));return n}
window.__mast=mast;mast();
window.addEventListener('storage',function(e){if(e.key==='wsx-learned'||e.key==='wsv2-anki')mast();if(e.key==='wsx-last')paintCont()});
// ---- 设置面板
var sheet=$('#sheet'),dim=$('#sdim'),gear=$('#gear');
function place(){if(window.innerWidth>900){var r=gear.getBoundingClientRect();sheet.style.top=Math.round(r.bottom+8)+'px';sheet.style.left=Math.round(Math.max(12,Math.min(r.right-360,window.innerWidth-372)))+'px'}else{sheet.style.top='';sheet.style.left=''}}
function openS(){sheet.hidden=false;dim.hidden=false;body.classList.add('sheet-open');place();sheet.scrollTop=0;var x=$('#sheetX');x&&x.focus({preventScroll:true})}
function closeS(){if(sheet.hidden)return;sheet.hidden=true;dim.hidden=true;body.classList.remove('sheet-open');gear&&gear.focus({preventScroll:true})}
window.__sheet={open:openS,close:closeS};
if(gear)gear.addEventListener('click',function(e){e.stopPropagation();sheet.hidden?openS():closeS()});
dim.addEventListener('click',closeS);$('#sheetX').addEventListener('click',closeS);
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeS()});
window.addEventListener('resize',function(){if(!sheet.hidden)place()});
var ty=null;sheet.addEventListener('touchstart',function(e){ty=sheet.scrollTop<=0?e.touches[0].clientY:null},{passive:true});
sheet.addEventListener('touchmove',function(e){if(ty!=null&&e.touches[0].clientY-ty>70){ty=null;closeS()}},{passive:true});
// 语速分段 → 同步隐藏的 #rate，让正在播放的音频立即变速
$('#rateseg').addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;var s=$('#rate');s.value=b.getAttribute('data-v');s.dispatchEvent(new Event('change'))});
window.__hdr={batch:LB,batchVisible:batchVisible,mast:mast,paintCont:paintCont};
})();</script><!--/v2hdr-->'''

THM_OLD = 'if(m)m.setAttribute("content",d?"#6e2f22":"#e0703a")'
THM_NEW = 'if(m)m.setAttribute("content",d?"#26231f":"#e7dfd3")'

def strip(s):
    s = re.sub(r'<!--v2pal-->.*?<!--/v2pal-->', '', s, flags=re.S)
    s = re.sub(r'<!--v2hdr-css-->.*?<!--/v2hdr-css-->', '', s, flags=re.S)
    s = re.sub(r'<!--v2hdr-->.*?<!--/v2hdr-->\n?', '', s, flags=re.S)
    return s

def common(s):
    s = strip(s)
    s = s.replace(THM_OLD, THM_NEW).replace('<meta name="theme-color" content="#e0703a">', '<meta name="theme-color" content="#e7dfd3">')
    s = s.replace('</head>', PAL + '</head>', 1)
    return s

# ---- index / anki
for f in ('index.html', 'anki.html'):
    s = common(rd(f)); wr(f, s); print('palette', f)

# ---- stories
s = common(rd('stories.html'))
if '<meta name="theme-color"' not in s:
    s = s.replace('<meta name="viewport" content="width=device-width,initial-scale=1">', '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#e7dfd3">', 1)
s = s.replace('</head>', HCSS + '</head>', 1)
# icon-only theme toggle on stories (behaviour unchanged)
s = s.replace('b.textContent=d?"☀️ 日间":"🌙 夜间"', 'b.textContent=d?"☀️":"🌙";b.setAttribute("aria-label",d?"切换到日间模式":"切换到夜间模式")', 1)
# latest batch (static fallback; runtime recomputes)
secs = re.findall(r'<section class="chap" id="c(\d+)" data-c="\d+" data-bt="([^"]*)"', s)
LB = ''
for n, b in secs:
    if b: LB = b
lb = [int(n) for n, b in secs if b == LB and LB]
LBN = sum(1 for v in W.values() if LB and v.get('bt') == LB)
NF, NL = (lb[0], lb[-1]) if lb else (1, 1)
first_ch = min(int(k) for k in CH)
hero = HERO.format(NCH=NCH, NW=NW, CT1=CT[str(first_ch)], NF=NF, NL=NL, NC=len(lb), LB=LB, LBN=LBN)
# header: old <header class="top">…</header> or already-converted hero
if '<div class="hero" id="hero">' in s:
    s = re.sub(r'<div class="hero" id="hero">.*?</section></div>', lambda m: hero, s, count=1, flags=re.S)
else:
    s, k = re.subn(r'<header class="top">.*?</header>', lambda m: hero, s, count=1, flags=re.S); assert k == 1, 'header anchor'
# toolbar
if '<div class="tools" id="toolbar">' in s:
    s, k = re.subn(r'<div class="tools" id="toolbar">.*?<select id="rate".*?</select></div>\n<div class="srow"><button class="stopb".*?</div>\n</div>', lambda m: TOOLS, s, count=1, flags=re.S)
else:
    s, k = re.subn(r'<div class="toolbar" id="toolbar">.*?</div>\n</div>\n(?=<div class="wrap">)', lambda m: TOOLS + '\n', s, count=1, flags=re.S)
assert k == 1, 'toolbar anchor'
# main script hooks
s = s.replace("$('#learnedN').textContent=tot+'/'+Object.keys(W).length;", "if(window.__mast)window.__mast();", 1)
if "var fv=$('#fsv')" not in s:
    s = s.replace("$('#rate').value=prefs.rate; save('wsx-prefs',prefs);", "$('#rate').value=prefs.rate; var fv=$('#fsv');if(fv)fv.textContent=prefs.fs+' px'; save('wsx-prefs',prefs);", 1)
assert "var fv=$('#fsv')" in s and 'window.__mast' in s
# usage tip: underline = latest batch only
s = s.replace('<span class="tw demo nwd">绿色下划线</span> / NEW = 这次新增的词', '<span class="tw demo nwb">绿色下划线</span> = <span data-x="lb">%s</span> 最新一批新增的词' % LB, 1)
s = re.sub(r'<span class="tw demo nwb">绿色下划线</span> = <span data-x="lb">[^<]*</span>', '<span class="tw demo nwb">绿色下划线</span> = <span data-x="lb">%s</span>' % LB, s, count=1)
# about: coverage line computed from data
cov = ('<li>覆盖：全书 <span data-x="ch">%d</span> 章把单词总表 <span data-x="w">%d</span> 个词条全部写进英文故事并高亮'
       '（其中 <span data-x="nw">%d</span> 个是旧词表里标 NEW 的词；最新一批 <span data-x="lb">%s</span> 新增 <span data-x="lbnn">%d</span> 个，在第 <span data-x="lbr2">%d–%d</span> 章）。</li>') % (NCH, NW, NNEW, LB, LBN, NF, NL)
s, k = re.subn(r'<li>覆盖：全书 (?:\d+|<span data-x="ch">\d+</span>) 章.*?</li>', lambda m: cov, s, count=1, flags=re.S); assert k == 1, 'about anchor'
# header script after navfix (needs window.__nav)
i = s.rfind('</body>'); s = s[:i] + HJS + '\n' + s[i:]
wr('stories.html', s); print('header', 'stories.html', 'chapters', NCH, 'words', NW, 'latest', LB, LBN, '%d-%d' % (NF, NL))
