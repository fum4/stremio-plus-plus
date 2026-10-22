from stremio_plus_plus.sources.candidates import parse
from stremio_plus_plus.sources.ranking import rank

IH = "6778f903610f20668ecdacea68162e974f0201a8"


def _torrentio(
    title: str, ih: str = IH, idx: int = 2, group: str | None = None
) -> dict[str, object]:
    hints: dict[str, object] = {"filename": title.split("\n")[0]}
    if group:
        hints["bingeGroup"] = group
    return {
        "name": "Torrentio\n4k",
        "title": title,
        "infoHash": ih,
        "fileIdx": idx,
        "sources": ["tracker:udp://tracker.example:1337/announce"],
        "behaviorHints": hints,
    }


def test_a_torrentio_entry_is_parsed_from_its_free_text() -> None:
    c = parse("torrentio", _torrentio("MobLand.S01E03.2160p.HEVC.mkv\n👤 199 💾 3.3 GB ⚙️ TPB"))
    assert c is not None
    assert (c.info_hash, c.file_index, c.height, c.seeders) == (IH, 2, 2160, 199)
    assert c.size_bytes == int(3.3 * (1 << 30))
    assert c.trackers == ("tracker:udp://tracker.example:1337/announce",)


def test_debrid_links_are_candidates_and_youtube_ids_are_not() -> None:
    debrid = parse("rd", {"name": "[RD+] 1080p", "url": "https://rd.example/dl/x.mkv"})
    assert debrid is not None and debrid.url and debrid.info_hash is None
    assert parse("yt", {"name": "trailer", "ytId": "abc"}) is None


def test_ranking_prefers_local_then_same_release_then_quality_then_seeders() -> None:
    a = parse("t", _torrentio("A.1080p.mkv\n👤 900", ih="a" * 40))
    b = parse("t", _torrentio("B.2160p.mkv\n👤 10", ih="b" * 40, group="grp"))
    c = parse("t", _torrentio("C.2160p.mkv\n👤 50", ih="c" * 40))
    assert a and b and c
    assert rank([a, b, c])[0] is c  # 4K, then seeders
    assert rank([a, b, c], last_group="grp")[0] is b  # same release as the last episode
    assert rank([a, b, c], local={"a" * 40: 1.0})[0] is a  # already on the laptop


def test_unplayable_and_dolby_vision_releases_sink() -> None:
    dv = parse("t", _torrentio("X.2160p.DV.mkv\n👤 999", ih="d" * 40))
    av1 = parse("t", _torrentio("X.1080p.AV1.mkv\n👤 999", ih="e" * 40))
    ok = parse("t", _torrentio("X.720p.mkv\n👤 1", ih="f" * 40))
    assert dv and av1 and ok
    assert rank([dv, av1, ok])[0] is ok
    assert not av1.playable and dv.dolby_vision


def test_uploader_names_are_not_resolutions_and_dubs_sink() -> None:
    raw = _torrentio("Al este del Eden [HDTV][Cap.101]\n👤 82 ⚙️ Wolfmax4k\n🇪🇸", ih="1" * 40)
    dub = parse("t", {**raw, "name": "Torrentio\nHDTV"})
    multi = parse("t", _torrentio("East.of.Eden.S01E01.2160p.mkv\n👤 30\n🇬🇧 / 🇷🇺", ih="2" * 40))
    assert dub and multi
    assert dub.height == 0 and not dub.english
    assert multi.english and multi.height == 2160


def test_a_poorly_seeded_4k_loses_to_a_well_seeded_1080p() -> None:
    thin = parse("t", _torrentio("X.2160p.mkv\n👤 12", ih="3" * 40))
    busy = parse("t", _torrentio("X.1080p.mkv\n👤 694", ih="4" * 40))
    assert thin and busy
    assert rank([thin, busy])[0] is busy
