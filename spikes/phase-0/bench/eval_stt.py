import sys, json, re, statistics
sys.path.insert(0, sys.argv[1]); from srtlib import parse
S = sys.argv[2]
def norm(t):
    t = t.lower().replace("’", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", t).split()
def lev(r, h):
    d = list(range(len(h)+1))
    for i in range(1, len(r)+1):
        prev, d[0] = d[0], i
        for j in range(1, len(h)+1):
            cur = d[j]
            d[j] = min(d[j]+1, d[j-1]+1, prev + (r[i-1] != h[j-1]))
            prev = cur
    return d[-1]
try:
    import jiwer
except ImportError:
    jiwer = None
ref = parse(f"{S}/dl/TOS-en.srt")
# drop on-screen caption (not speech) from cue 9
ref = [(s, e, t.replace('"Fourty years later"', '').strip()) for s, e, t in ref]
ref_words = [w for _, _, t in ref for w in norm(t)]
def parakeet_words(p):
    d = json.load(open(p)); out = []
    for sen in d["sentences"]:
        for tok in sen["tokens"]:
            if tok["text"].startswith(" ") or not out:
                out.append([tok["text"], tok["start"], tok["end"]])
            else:
                out[-1][0] += tok["text"]; out[-1][2] = tok["end"]
    return [(w, s, e) for w, s, e in out if norm(w)]
def whisper_words(p):
    d = json.load(open(p))
    return [(w["word"], w["start"], w["end"]) for seg in d["segments"] for w in seg.get("words", []) if norm(w["word"])]
systems = {
  "parakeet-tdt-0.6b-v3 (default)": (f"{S}/out/parakeet_run2/tos_10min_16k.srt", parakeet_words(f"{S}/out/parakeet_run2/tos_10min_16k.json")),
  "parakeet subtitle-style segmentation": (f"{S}/out/parakeet_subtitle_style/tos_10min_16k.srt", parakeet_words(f"{S}/out/parakeet_run2/tos_10min_16k.json")),
  "whisper-large-v3-turbo (CLI default)": (f"{S}/out/whisper_run2/tos_10min_16k.srt", whisper_words(f"{S}/out/whisper_run2/tos_10min_16k.json")),
  "whisper-large-v3-turbo (no-cond + halluc-thr 2)": (f"{S}/out/whisper_nocond/tos_10min_16k.srt", whisper_words(f"{S}/out/whisper_nocond/tos_10min_16k.json")),
}
print(f"reference: {len(ref)} cues, {len(ref_words)} words (caption 'Fourty years later' removed)\n")
print("| system | hyp words (all) | WER all-text (own) | WER all-text (jiwer) | WER in-cue-window ±1s | cues covered (SRT segment overlap) | cues covered (word timestamp in cue) | median abs cue-start err (s) | p90 abs cue-start err (s) |")
print("|---|---|---|---|---|---|---|---|---|")
percue = {}
for name, (srtp, words) in systems.items():
    segs = parse(srtp)
    hyp_all = [w for _, _, t in segs for w in norm(t)]
    wer = lev(ref_words, hyp_all) / len(ref_words)
    jw = jiwer.wer(" ".join(ref_words), " ".join(hyp_all)) if jiwer else float("nan")
    inwin = [w for w, s, e in words if any(rs-1.0 <= (s+e)/2 <= re_+1.0 for rs, re_, _ in ref)]
    hyp_win = [x for w in inwin for x in norm(w)]
    werw = lev(ref_words, hyp_win) / len(ref_words)
    cov_seg = sum(any(ss < re_ and se > rs for ss, se, _ in segs) for rs, re_, _ in ref) / len(ref)
    cov_w = sum(any(rs <= (s+e)/2 <= re_ for _, s, e in words) for rs, re_, _ in ref) / len(ref)
    errs = []
    pc = []
    for rs, re_, t in ref:
        cand = [s for _, s, e in words if rs-1.0 <= s <= re_]
        if cand: errs.append(abs(min(cand) - rs))
        pc.append(" ".join(w.strip() for w, s, e in words if rs-0.1 <= (s+e)/2 <= re_+0.1))
    percue[name] = pc
    errs.sort()
    p90 = errs[int(round(0.9*(len(errs)-1)))]
    print(f"| {name} | {len(hyp_all)} | {wer:.1%} | {jw:.1%} | {werw:.1%} | {cov_seg:.1%} | {cov_w:.1%} | {statistics.median(errs):.2f} (n={len(errs)}) | {p90:.2f} |")
print()
keys = ["parakeet-tdt-0.6b-v3 (default)", "whisper-large-v3-turbo (CLI default)", "whisper-large-v3-turbo (no-cond + halluc-thr 2)"]
diff = [i for i, (s, e, t) in enumerate(ref) if max(lev(norm(t), norm(percue[k][i])) for k in keys) >= 2]
print(f"cues where at least one system has >=2 word edits vs reference (normalized; hyp words with midpoint in cue +-0.1s): {len(diff)}/{len(ref)}")
pick = [diff[int(j*(len(diff)-1)/4)] for j in range(5)]
for i in pick:
    s, e, t = ref[i]
    print(f"\n[{s:.1f}-{e:.1f}s] REF: {t}")
    for k in keys: print(f"  {k}: {percue[k][i] or '(nothing)'}")
