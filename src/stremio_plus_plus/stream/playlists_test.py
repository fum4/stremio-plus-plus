from stremio_plus_plus.stream import playlists
from stremio_plus_plus.stream.media import Media

MEDIA = Media(
    duration_s=13.5,
    start_s=0.0,
    video_codec="hevc",
    video_tag="hvc1.2.4.L150.B0",
    width=3840,
    height=1604,
    audio_index=0,
    audio_codec="eac3",
    audio_tag="ec-3",
    audio_args=("-c:a", "copy"),
)


def test_master_turns_the_subtitle_rendition_on_by_default() -> None:
    text = playlists.master(MEDIA, "ron")
    assert "DEFAULT=YES,AUTOSELECT=YES" in text
    assert 'CODECS="hvc1.2.4.L150.B0,ec-3",SUBTITLES="subs"' in text


def test_media_playlists_list_every_segment_up_front() -> None:
    video = playlists.video(MEDIA)
    assert "#EXT-X-PLAYLIST-TYPE:VOD" in video and video.endswith("#EXT-X-ENDLIST\n")
    assert [line for line in video.splitlines() if line.endswith(".ts")] == [
        "v0.ts",
        "v1.ts",
        "v2.ts",
    ]
    assert "#EXTINF:1.500," in video  # the remainder
    assert "s2.vtt" in playlists.subtitles(MEDIA)


def test_vtt_maps_cue_time_zero_to_the_segments_timestamp_origin() -> None:
    text = playlists.vtt(MEDIA, [(61.5, 63.25, "Bună")])
    assert text.startswith("WEBVTT\nX-TIMESTAMP-MAP=MPEGTS:0,LOCAL:00:00:00.000\n")
    assert "00:01:01.500 --> 00:01:03.250\nBună" in text
