"""Which 2-minute chunk to generate next: the playhead's first, then ahead, then back-fill.

Resuming mid-episode starts generating where the viewer is instead of from minute zero.
"""


def chunk_count(duration_s: float, chunk_s: int) -> int:
    return max(1, -(-int(duration_s) // chunk_s))


def next_chunk(done: set[int], total: int, playhead_chunk: int) -> int | None:
    playhead_chunk = min(max(playhead_chunk, 0), total - 1)
    for i in range(playhead_chunk, total):
        if i not in done:
            return i
    for i in range(playhead_chunk - 1, -1, -1):
        if i not in done:
            return i
    return None
