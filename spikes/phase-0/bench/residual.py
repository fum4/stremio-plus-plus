import sys, statistics; sys.path.insert(0, sys.argv[1])
from srtlib import parse
ref = parse(sys.argv[2])
for p in sys.argv[3:]:
    out = parse(p)
    if len(out) != len(ref): print(p, 'CUE COUNT MISMATCH', len(out), len(ref)); continue
    d = sorted(abs(o[0]-r[0]) for o, r in zip(out, ref))
    p90 = d[min(len(d)-1, int(round(0.9*(len(d)-1))))]
    sd = [o[0]-r[0] for o, r in zip(out, ref)]
    print(f'{p.split("/")[-1]}: n={len(d)} median_abs={statistics.median(d):.3f}s p90_abs={p90:.3f}s max_abs={d[-1]:.3f}s signed_first={sd[0]:+.3f} signed_last={sd[-1]:+.3f}')
