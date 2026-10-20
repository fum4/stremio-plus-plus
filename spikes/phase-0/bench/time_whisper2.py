import sys, time, resource
import mlx_whisper
kw = dict(path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en", word_timestamps=True, verbose=False, condition_on_previous_text=False, hallucination_silence_threshold=2)
for i in range(2):
    a = time.perf_counter(); r = mlx_whisper.transcribe(sys.argv[1], **kw); b = time.perf_counter()
    print(f"call{i+1}: {b-a:.2f}s segments={len(r['segments'])}", flush=True)
print(f"maxrss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:.0f}MiB")
