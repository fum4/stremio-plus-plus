import sys, time, resource
t0 = time.perf_counter()
from parakeet_mlx import from_pretrained
t1 = time.perf_counter()
model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
t2 = time.perf_counter()
r = model.transcribe(sys.argv[1], chunk_duration=120, overlap_duration=15)
t3 = time.perf_counter()
r = model.transcribe(sys.argv[1], chunk_duration=120, overlap_duration=15)
t4 = time.perf_counter()
print(f"import={t1-t0:.2f}s load={t2-t1:.2f}s transcribe1={t3-t2:.2f}s transcribe2={t4-t3:.2f}s maxrss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:.0f}MiB sentences={len(r.sentences)}")
