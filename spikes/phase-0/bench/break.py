import sys; sys.path.insert(0, sys.argv[1])
from srtlib import parse, write
ref, outdir = sys.argv[2], sys.argv[3]
c = parse(ref)
write([(s+3.7, e+3.7, t) for s, e, t in c], outdir + '/broken_a_offset3.7.srt')
k = 25/23.976
write([(s*k+2.0, e*k+2.0, t) for s, e, t in c], outdir + '/broken_b_offset2_drift.srt')
print(len(c), 'cues; last ref start', c[-1][0], '-> b', c[-1][0]*k+2)
