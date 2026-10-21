import re, sys
TS = re.compile(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)')
def t(h,m,s,ms): return int(h)*3600+int(m)*60+int(s)+int(ms.ljust(3,'0')[:3])/1000
def parse(path):
    txt = open(path, encoding='utf-8-sig', errors='replace').read().replace('\r','')
    cues=[]
    for block in re.split(r'\n\s*\n', txt):
        lines=block.strip('\n').split('\n')
        for i,l in enumerate(lines):
            m=TS.search(l)
            if m:
                g=m.groups(); cues.append((t(*g[:4]), t(*g[4:]), '\n'.join(lines[i+1:]).strip())); break
    return cues
def fmt(x):
    x=max(0,x); ms=int(round(x*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'
def write(cues, path):
    with open(path,'w',encoding='utf-8') as f:
        for i,(a,b,tx) in enumerate(cues,1): f.write(f'{i}\n{fmt(a)} --> {fmt(b)}\n{tx}\n\n')
if __name__=='__main__':  # clip: in out maxsec
    c=[x for x in parse(sys.argv[1]) if x[0] < float(sys.argv[3])]
    c=[(a,min(b,float(sys.argv[3])),tx) for a,b,tx in c]
    write(c, sys.argv[2]); print(sys.argv[2], len(c))
