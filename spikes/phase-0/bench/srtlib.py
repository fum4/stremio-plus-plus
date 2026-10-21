import re, sys
TS = re.compile(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)')
def parse(path):
    txt = open(path, encoding='utf-8-sig', errors='replace').read().replace('\r\n', '\n').replace('\r', '\n')
    cues = []
    for block in re.split(r'\n\s*\n', txt.strip()):
        lines = block.split('\n')
        for i, l in enumerate(lines):
            m = TS.search(l)
            if m:
                g = [int(x) for x in m.groups()]
                s = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
                e = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
                cues.append((s, e, ' '.join(lines[i+1:]).strip()))
                break
    return cues
def fmt(t):
    t = max(0, t); ms = int(round(t*1000))
    return '%02d:%02d:%02d,%03d' % (ms//3600000, ms//60000%60, ms//1000%60, ms%1000)
def write(cues, path):
    with open(path, 'w') as f:
        for i, (s, e, t) in enumerate(cues, 1):
            f.write(f'{i}\n{fmt(s)} --> {fmt(e)}\n{t}\n\n')
