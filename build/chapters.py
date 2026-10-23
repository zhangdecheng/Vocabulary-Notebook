"""Parse chapters/chNN.txt (story source format) and validate against new words."""
import re,json,glob,os
TAG=re.compile(r'\{([^{}|]+)\|(\d+)\}')
def parse(path):
    ch={'paras':[],'words':{}};cur=None
    for ln in open(path,encoding='utf-8'):
        ln=ln.rstrip('\n')
        if not ln.strip():continue
        if ln.startswith('# '):
            no,th,te,tz=[x.strip() for x in ln[2:].split('|')]
            ch.update(no=int(no),theme=th,title_en=te,title_zh=tz)
        elif ln.startswith('P: '):ch['paras'].append([ln[3:],None])
        elif ln.startswith('Z: '):ch['paras'][-1][1]=ln[3:]
        elif ln.startswith('W: '):
            a=[x.strip() for x in ln[3:].split('|')]
            cur=a[0];ch['words'][cur]={'p':a[1],'gl':a[2],'k':a[3] if len(a)>3 else '','x':[]}
        elif ln.startswith('X: '):
            en,zh=[x.strip() for x in ln[3:].split('|')];ch['words'][cur]['x'].append([en,zh])
        else: raise ValueError(path+': bad line '+ln[:60])
    return ch
def tagged(ch):
    out=[]
    for en,zh in ch['paras']:
        out+= [m.group(2) for m in TAG.finditer(en)]
    return out
def validate(path,newids):
    ch=parse(path);errs=[]
    t=tagged(ch)
    for i in set(t):
        if i not in newids: errs.append('tag not new id '+i)
        if i not in ch['words']: errs.append('no W for '+i)
    for i,w in ch['words'].items():
        if i not in t: errs.append('W not in story '+i)
        if len(w['x'])<2: errs.append('x<2 '+i)
    for en,zh in ch['paras']:
        if not zh: errs.append('missing Z')
    return ch,errs
if __name__=='__main__':
    import sys
    d=json.load(open(sys.argv[1]))
    newids={r['#'] for r in d['new']}
    seen={}
    for p in sorted(glob.glob(os.path.join(os.path.dirname(__file__),'chapters','ch*.txt'))):
        ch,errs=validate(p,newids)
        for i in ch['words']: seen.setdefault(i,[]).append(ch['no'])
        print(os.path.basename(p),ch['no'],ch['title_en'],len(ch['words']),'words',len(ch['paras']),'paras',errs or 'OK')
    print('covered',len(seen),'/',len(newids),'dups',{k:v for k,v in seen.items() if len(v)>1})
    miss=sorted(newids-set(seen),key=int);print('missing',len(miss))
