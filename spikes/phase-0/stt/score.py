import json, re, sys, statistics as st
sys.path.insert(0, '/tmp/stremio-companion-stt/scripts')
from srtlib import parse

CLIP = 600.0
REF = sys.argv[1]
HYPS = sys.argv[2:]  # name=path.json

def norm_words(s):
    s = s.lower().replace('’', "'")
    s = re.sub(r"[-–—/]", ' ', s)
    s = re.sub(r"[^\w\s]", '', s)  # strips apostrophes too (both sides)
    return s.split()

def clean_ref(text):
    text = re.sub(r'<[^>]+>', '', text)
    out = []
    for line in text.split('\n'):
        if '♪' in line or re.match(r'^\s*\*.*\*\s*$', line):
            continue
        line = re.sub(r'\[[^\]]*\]', ' ', line)
        line = re.sub(r'\([^)]*\)', ' ', line)
        line = re.sub(r'^\s*-\s*', '', line)
        line = re.sub(r"^\s*[A-Z][A-Z0-9 .'\-]{1,30}:\s*", '', line)
        out.append(line.strip())
    return ' '.join(x for x in out if x)

ref_cues = []
for a, b, t in parse(REF):
    if a >= CLIP: continue
    w = norm_words(clean_ref(t))
    if w: ref_cues.append((a, min(b, CLIP), clean_ref(t), w))

ref_words = []  # (word, mid, cue_idx, is_first)
for ci, (a, b, t, w) in enumerate(ref_cues):
    n = len(w)
    for i, x in enumerate(w):
        ref_words.append((x, a + (b - a) * (i + 0.5) / n, ci, i == 0))

def load_hyp(path):
    d = json.load(open(path))
    segs, words = [], []
    for s in d['segments']:
        if s['start'] >= CLIP: continue
        segs.append((s['start'], s['end'], s['text'].strip()))
        for wd in s.get('words', []):
            for x in norm_words(wd['word']):
                words.append((x, wd['start'], wd['end']))
    return segs, words

def align(r, h):
    n, m = len(r), len(h)
    D = [list(range(m + 1))] + [[i] + [0] * m for i in range(1, n + 1)]
    for i in range(1, n + 1):
        Di, Dp, ri = D[i], D[i - 1], r[i - 1]
        for j in range(1, m + 1):
            Di[j] = min(Dp[j - 1] + (ri != h[j - 1]), Dp[j] + 1, Di[j - 1] + 1)
    i, j, ops = n, m, []
    while i or j:
        if i and j and D[i][j] == D[i - 1][j - 1] + (r[i - 1] != h[j - 1]):
            ops.append(('C' if r[i - 1] == h[j - 1] else 'S', i - 1, j - 1)); i -= 1; j -= 1
        elif i and D[i][j] == D[i - 1][j] + 1:
            ops.append(('D', i - 1, None)); i -= 1
        else:
            ops.append(('I', None, j - 1)); j -= 1
    ops.reverse()
    c = {k: sum(1 for o in ops if o[0] == k) for k in 'CSDI'}
    return ops, c

def wer(c, n): return (c['S'] + c['D'] + c['I']) / n

def near_cue(t, pad=1.0):
    return any(a - pad <= t <= b + pad for a, b, _, _ in ref_cues)

def pct(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k)
    return xs[f] + (xs[min(f + 1, len(xs) - 1)] - xs[f]) * (k - f)

R = [w[0] for w in ref_words]
results, hypdata = {}, {}
for spec in HYPS:
    name, path = spec.split('=')
    segs, words = load_hyp(path)
    hypdata[name] = (segs, words)
    H = [w[0] for w in words]
    ops, c = align(R, H)
    hw = [w for w in words if near_cue((w[1] + w[2]) / 2)]
    ops2, c2 = align(R, [w[0] for w in hw])
    covered = sum(1 for a, b, _, _ in ref_cues if any(s < b and e > a for s, e, _ in segs))
    # cue start error via first word of each cue aligned as exact match
    errs = [words[j][1] - ref_words[i][1] + 0 for (k, i, j) in ops if k == 'C' and ref_words[i][3]]
    # convert: ref_words mid -> use cue start instead
    errs = []
    for k, i, j in ops:
        if k == 'C' and ref_words[i][3]:
            errs.append(words[j][1] - ref_cues[ref_words[i][2]][0])
    seg_err = [min(abs(s - a) for s, _, _ in segs) for a, _, _, _ in ref_cues]
    outside = [(s, e, t) for s, e, t in segs if not any(a - 1 <= e and s <= b + 1 for a, b, _, _ in ref_cues)]
    # repetition: same normalized segment text consecutive, or a 3-gram repeated >=3 times in one segment
    reps = []
    for idx, (s, e, t) in enumerate(segs):
        w = norm_words(t)
        grams = [tuple(w[i:i + 3]) for i in range(len(w) - 2)]
        if grams and max(grams.count(g) for g in grams) >= 3: reps.append((s, t))
        if idx and norm_words(segs[idx - 1][2]) == w and len(w) > 1: reps.append((s, t))
    results[name] = dict(n_ref=len(R), n_hyp=len(H), C=c, wer=wer(c, len(R)), C2=c2, wer2=wer(c2, len(R)),
                         n_hyp2=len(hw), cues=len(ref_cues), covered=covered, n_err=len(errs),
                         med_abs=st.median(map(abs, errs)), p90_abs=pct(list(map(abs, errs)), .9),
                         med_signed=st.median(errs), seg_med=st.median(seg_err), seg_p90=pct(seg_err, .9),
                         n_segs=len(segs), outside=outside, reps=reps)

print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('outside', 'reps')} for k, v in results.items()}, indent=1))
for k, v in results.items():
    print(f'\n## {k}: segments with no ref cue within ±1 s ({len(v["outside"])})')
    for s, e, t in v['outside']: print(f'  [{s:7.2f}-{e:7.2f}] {t}')
    print(f'## {k}: repetition flags ({len(v["reps"])})')
    for s, t in v['reps']: print(f'  [{s:7.2f}] {t}')

# examples: cues where centre and downmix normalized text differ
names = list(hypdata)
def words_in(name, a, b):
    return ' '.join(x for x, s, e in hypdata[name][1] if a - 0.3 <= (s + e) / 2 <= b + 0.3)
diffs = []
for a, b, t, w in ref_cues:
    outs = [words_in(n, a, b) for n in names]
    if len(set(outs)) > 1: diffs.append((a, b, t, outs))
print(f'\n## cues where outputs differ: {len(diffs)} of {len(ref_cues)}')
step = max(1, len(diffs) // 8)
for a, b, t, outs in diffs[::step][:8]:
    print(f'\n[{a:06.2f}-{b:06.2f}] REF: {t}')
    for n, o in zip(names, outs): print(f'   {n:8}: {o}')
