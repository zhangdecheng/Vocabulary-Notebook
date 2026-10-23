import csv,json,html,re,sys
def norm(w): return re.sub(r'\s+',' ',html.unescape(w)).strip().lower()
def load_csv(p):
    rows=list(csv.DictReader(open(p,encoding='utf-8-sig')))
    for r in rows:
        r['单词']=re.sub(r'\s+',' ',html.unescape(r['单词'])).strip()
        for k in ('中文','笔记线索','音标'): r[k]=html.unescape(r[k] or '').strip()
    return rows
def diff(csvp,wordsjson):
    rows=load_csv(csvp); W=json.load(open(wordsjson,encoding='utf-8'))['W']
    live={norm(v['w']):k for k,v in W.items()}
    new=[];changed=[];matched={}
    for r in rows:
        n=norm(r['单词'])
        if n in live:
            k=live[n];v=W[k];matched[n]=k;ch=[]
            dates=[d.strip() for d in r['出现日期'].split(' / ') if d.strip()]
            if dates!=v.get('d',[]): ch.append('出现日期')
            if r['中文']!=v.get('z'): ch.append('中文')
            if r['主题'] not in v.get('t',[]): ch.append('主题')
            if ch: changed.append((k,v['w'],ch))
        else: new.append(r)
    removed=[(k,v['w']) for k,v in W.items() if norm(v['w']) not in matched]
    return rows,new,changed,removed
if __name__=='__main__':
    rows,new,changed,removed=diff(sys.argv[1],sys.argv[2])
    import collections
    print('master',len(rows),'new',len(new),'changed',len(changed),'removed',len(removed))
    print('changed fields',collections.Counter(f for c in changed for f in c[2]))
    print('removed',removed)
    json.dump({'new':new,'changed':changed,'removed':removed},open(sys.argv[3],'w'),ensure_ascii=False,indent=0)
