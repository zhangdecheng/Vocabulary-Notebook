#!/usr/bin/env python3
"""stories.html 章节切换修复（幂等）：修复手机目录抽屉无法滚动 + 章节条(上一章/下一章/选章) + 章末导航 + 继续阅读。
用法：python3 build/navfix.py site/stories.html   （原地修改；不动故事内容、词数据、音频、Anki）"""
import sys, re
p = sys.argv[1]; s = open(p, encoding='utf-8').read()
M = '<!--navfix-->'
if M in s:
    s = re.sub(r'<!--navfix-->.*?<!--/navfix-->\n?', '', s, flags=re.S)
    s = re.sub(r'/\*navfix-css\*/.*?/\*/navfix-css\*/', '', s, flags=re.S)
CSS = '''/*navfix-css*/
#tocscrim{display:none}
.tocx{display:none;float:right;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;width:30px;height:28px;font-size:15px;cursor:pointer;margin:-4px 0 0}
.tocq{display:flex;flex-wrap:wrap;gap:6px;padding:0 8px 10px}
.tocq button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:4px 10px;font-size:12.5px;cursor:pointer}
.tocq button.pri{background:var(--acc);border-color:var(--acc);color:var(--on-acc,#fff);font-weight:600}
.tocq button.nb{border-color:var(--acc-t,#e0703a);color:var(--acc-t,#e0703a)}
#chbar{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);width:min(440px,calc(100vw - 32px));z-index:44;display:flex;align-items:stretch;background:var(--card);border:1px solid var(--bd,var(--line));border-radius:999px;box-shadow:0 6px 22px rgba(60,40,20,.18);overflow:hidden;transition:opacity .2s,transform .2s}
#chbar.hide{opacity:0;pointer-events:none}
#chbar button{border:0;background:none;color:var(--ink);cursor:pointer;font:inherit}
#chbar .cbp,#chbar .cbn{flex:none;width:44px;font-size:20px;color:var(--acc-t,var(--acc))}
#chbar .cbp:disabled,#chbar .cbn:disabled{opacity:.3;cursor:default}
#chbar .cbt{flex:1;min-width:0;padding:6px 4px;display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1.2;border-left:1px solid var(--line);border-right:1px solid var(--line)}
#chbar .cbt b{font-size:11px;color:var(--acc-t,var(--acc));letter-spacing:.5px;font-weight:700}
#chbar .cbt span{font-size:13.5px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#chbar.resume .cbp,#chbar.resume .cbn{display:none}#chbar.resume .cbt{background:var(--acc);color:var(--on-acc,#fff);border:0;padding:8px 14px}#chbar.resume .cbt b{color:var(--on-acc,#fff);opacity:.9}
.chnav{display:flex;gap:10px;margin-top:22px;padding-top:16px;border-top:1px dashed var(--line)}
.chnav a{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;text-decoration:none;color:var(--ink);border:1px solid var(--line);background:var(--bg);border-radius:12px;padding:10px 12px}
.chnav a:hover{border-color:var(--acc)}
.chnav a small{color:var(--acc-t,var(--acc));font-weight:700;font-size:12px}
.chnav a span{font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chnav a.nx{text-align:right;align-items:flex-end}.chnav .sp{flex:1}
.chnav .ct{flex:none;align-self:center;border:1px solid var(--line);background:var(--card);color:var(--mut);border-radius:999px;padding:6px 10px;font-size:12.5px;cursor:pointer}
html[data-theme=dark] #chbar{box-shadow:0 6px 22px rgba(0,0,0,.5)}
html[data-theme=dark] .chnav a{background:var(--bg)}
@media print{#chbar,.chnav,#tocscrim{display:none!important}}
.wrap{padding-bottom:90px}
@media (max-width:900px){
 .toc{align-self:auto;height:100vh;height:100dvh;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding-bottom:90px}
 body.toc-open{overflow:hidden}
 #tocscrim{display:block;position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:39;opacity:0;pointer-events:none;transition:opacity .2s}
 body.toc-open #tocscrim{opacity:1;pointer-events:auto}
 #chbar{left:72px;right:66px;bottom:20px;transform:none;width:auto}
 .tocx{display:inline-block}
}
/*/navfix-css*/'''
s = s.replace('</style><!--thm--><style>', CSS + '</style><!--thm--><style>', 1) if '</style><!--thm--><style>' in s else s.replace('</style>', CSS + '</style>', 1)
JS = r'''<!--navfix--><div id="tocscrim"></div>
<div id="chbar" class="hide" role="navigation" aria-label="章节切换"><button class="cbp" type="button" aria-label="上一章">‹</button><button class="cbt" type="button" aria-label="选择章节"><b></b><span></span></button><button class="cbn" type="button" aria-label="下一章">›</button></div>
<script>(function(){
var $=function(q,r){return (r||document).querySelector(q)},$$=function(q,r){return Array.prototype.slice.call((r||document).querySelectorAll(q))};
var body=document.body,toc=$('#toc'),bar=$('#chbar'),KEY='wsx-last';
var CH=$$('section.chap').map(function(c){var n=+c.getAttribute('data-c'),h=$('h2 small',c);return {n:n,el:c,zh:h?h.textContent:(''+n),bt:c.getAttribute('data-bt')||''}});
var idx={};CH.forEach(function(c,i){idx[c.n]=i});
function last(){try{var v=JSON.parse(localStorage.getItem(KEY)||'null');return v&&idx[v.c]!=null?v:null}catch(e){return null}}
function curPara(n){var i=idx[n];if(i==null)return '';var ps=$$('.para',CH[i].el),h=window.innerHeight;for(var k=0;k<ps.length;k++){var r=ps[k].getBoundingClientRect();if(r.bottom>h*0.15&&r.top<h*0.85)return ps[k].id}return ''}
function remember(n,p){try{localStorage.setItem(KEY,JSON.stringify({c:n,p:p===undefined?curPara(n):p,t:Date.now()}))}catch(e){}}
function go(n,pid){var i=idx[n];if(i==null)return;closeToc();var el=CH[i].el,pe=pid&&document.getElementById(pid);if(pe&&CH[i].el.contains(pe)){el=pe}else pid='';
  if(history.replaceState)history.replaceState(null,'','#'+(pid||'c'+n));
  var y=el.getBoundingClientRect().top+window.pageYOffset-stickyH();try{window.scrollTo({top:Math.max(0,y),left:0,behavior:'instant'})}catch(e){window.scrollTo(0,Math.max(0,y))}remember(n,pid||'');cur=n;paint();if(pid){el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash')}}
window.__nav={go:go,para:curPara,list:function(){return CH.map(function(c){return c.n})},cur:function(){return cur},last:last};
function stickyH(){var e=document.querySelector(window.innerWidth>=1024?'#toolbar':'.tb');if(e&&getComputedStyle(e).position==='sticky')return Math.ceil(e.getBoundingClientRect().height)+8;return window.innerWidth>900?70:12}
function closeToc(){body.classList.remove('toc-open')}
function openToc(){body.classList.add('toc-open');var a=$('.toc a[data-c="'+(cur||((last()||{}).c)||1)+'"]');if(a&&toc){toc.scrollTop=Math.max(0,a.offsetTop-toc.clientHeight/3)}}
// 1) drawer extras: close button + quick jumps
if(toc&&!$('.tocq',toc)){var h=$('.toch',toc);if(h){var x=document.createElement('button');x.className='tocx';x.type='button';x.setAttribute('aria-label','关闭目录');x.textContent='✕';h.insertBefore(x,h.firstChild);x.addEventListener('click',function(e){e.stopPropagation();closeToc()})}
  var q=document.createElement('div');q.className='tocq';var L=last(),firstNew=CH.filter(function(c){return c.bt})[0],lastNew=CH.filter(function(c){return c.bt}).slice(-1)[0];
  q.innerHTML=(L?'<button type="button" class="pri" data-go="'+L.c+'" data-p="'+(L.p||'')+'">▶ 继续阅读 · 第 '+L.c+' 章</button>':'')+'<button type="button" data-go="1">第 1 章</button>'+(firstNew?'<button type="button" class="nb" data-go="'+firstNew.n+'">新 '+firstNew.bt+' · 第 '+firstNew.n+'–'+lastNew.n+' 章</button>':'');
  if(h)h.parentNode.insertBefore(q,h.nextSibling);
  q.addEventListener('click',function(e){var b=e.target.closest('[data-go]');if(b){e.preventDefault();e.stopPropagation();go(+b.getAttribute('data-go'),b.getAttribute('data-p')||'')}})}
if(toc)toc.addEventListener('click',function(e){var a=e.target.closest('a[data-c]');if(a){e.preventDefault();go(+a.getAttribute('data-c'))}});
$('#tocscrim').addEventListener('click',closeToc);
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeToc()});
// 2) end-of-chapter prev/next
CH.forEach(function(c,i){if($('.chnav',c.el))return;var p=CH[i-1],n=CH[i+1],d=document.createElement('nav');d.className='chnav';d.setAttribute('aria-label','章节导航');
  d.innerHTML=(p?'<a class="pv" href="#c'+p.n+'" data-go="'+p.n+'"><small>‹ 上一章 · 第 '+p.n+' 章</small><span>'+p.zh+'</span></a>':'<span class="sp"></span>')+'<button type="button" class="ct">目录</button>'+(n?'<a class="nx" href="#c'+n.n+'" data-go="'+n.n+'"><small>下一章 · 第 '+n.n+' 章 ›</small><span>'+n.zh+'</span></a>':'<span class="sp"></span>');
  c.el.appendChild(d)});
document.addEventListener('click',function(e){var a=e.target.closest('.chnav [data-go]');if(a){e.preventDefault();go(+a.getAttribute('data-go'));return}
  if(e.target.closest('.chnav .ct')){e.preventDefault();e.stopPropagation();if(window.innerWidth>900){var t=$('.toc a[data-c="'+cur+'"]');if(t)t.scrollIntoView({block:'center'})}openToc()}});
// 3) sticky chapter bar + current chapter tracking + 继续阅读
var cur=0,saveT=0;
function detect(){var y=window.innerHeight*0.35,n=0;for(var i=0;i<CH.length;i++){var r=CH[i].el.getBoundingClientRect();if(r.top<=y){if(r.bottom>0)n=CH[i].n}else break}return n}
function paint(){var i=idx[cur],L=last(),tb=$('b',bar),ts=$('span',bar),bp=$('.cbp',bar),bn=$('.cbn',bar);
  if(i==null){if(document.getElementById('cont')){bar.className='resume hide';bp.disabled=true;bn.disabled=true;return}if(L){bar.className='resume';tb.textContent='继续阅读';ts.textContent='第 '+L.c+' 章 · '+CH[idx[L.c]].zh+(L.p&&/p(\d+)$/.test(L.p)?' · 第 '+(+/p(\d+)$/.exec(L.p)[1]+1)+' 段':'')}else{bar.className='resume';tb.textContent='开始阅读';ts.textContent='第 1 章 · '+CH[0].zh}
    bp.disabled=true;bn.disabled=true;return}
  bar.className='';var c=CH[i];tb.textContent='第 '+c.n+' / '+CH[CH.length-1].n+' 章'+(c.bt?' · 新 '+c.bt:'');ts.textContent=c.zh+' ▾';bp.disabled=i===0;bn.disabled=i===CH.length-1}
function onScroll(){var n=detect();if(n!==cur){cur=n;paint();}clearTimeout(saveT);if(n)saveT=setTimeout(function(){remember(n)},1000)}
var tk=0;window.addEventListener('scroll',function(){if(tk)return;tk=requestAnimationFrame(function(){tk=0;onScroll()})},{passive:true});
window.addEventListener('resize',onScroll);
$('.cbp',bar).addEventListener('click',function(e){e.stopPropagation();var i=idx[cur];if(i>0)go(CH[i-1].n)});
$('.cbn',bar).addEventListener('click',function(e){e.stopPropagation();var i=idx[cur];if(i!=null&&i<CH.length-1)go(CH[i+1].n)});
$('.cbt',bar).addEventListener('click',function(e){e.stopPropagation();if(idx[cur]==null){var L=last();if(L)go(L.c,L.p||'');else go(CH[0].n);return}
  if(window.innerWidth>900){var t=$('.toc a[data-c="'+cur+'"]');if(t&&toc)toc.scrollTop=Math.max(0,t.offsetTop-toc.clientHeight/3);t&&t.focus&&t.focus()}else openToc()});
var m=$('#menu');if(m)m.addEventListener('click',function(){setTimeout(function(){if(body.classList.contains('toc-open'))openToc()},0)});
onScroll();paint();
window.addEventListener('hashchange',function(){var mm=/^#c(\d+)$/.exec(location.hash);if(mm&&idx[+mm[1]]!=null){remember(+mm[1],'')}});
})();</script><!--/navfix-->
'''
i = s.find('<!--v2hdr-->')
if i < 0: i = s.rfind('</body>')
s = s[:i] + JS + s[i:]
open(p, 'w', encoding='utf-8').write(s); print('patched', p, len(s))
