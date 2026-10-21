import sys, time, resource
t0 = time.perf_counter()
import mlx_whisper
from mlx_whisper.load_models import load_model
import mlx.core as mx
t1 = time.perf_counter()
m = load_model("mlx-community/whisper-large-v3-turbo", dtype=mx.float16)
t2 = time.perf_counter()
kw = dict(path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en", word_timestamps=True, verbose=None)
for label, extra in [("default", {}), ("nocond", dict(condition_on_previous_text=False, hallucination_silence_threshold=2))]:
    a = time.perf_counter(); r = mlx_whisper.transcribe(sys.argv[1], **kw, **extra); b = time.perf_counter()
    print(f"{label}: transcribe={b-a:.2f}s segments={len(r['segments'])}")
print(f"import={t1-t0:.2f}s standalone_load={t2-t1:.2f}s maxrss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:.0f}MiB")
