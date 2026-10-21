from stremio_plus_plus.tv.discover import classify, parse_response


def test_parses_an_ssdp_reply() -> None:
    raw = (
        b"HTTP/1.1 200 OK\r\nCACHE-CONTROL: max-age=1800\r\n"
        b"LOCATION: http://192.168.1.134:7676/rcr/\r\n"
        b"SERVER: SHP, UPnP/1.0, Samsung UPnP SDK/1.0\r\n"
        b"ST: urn:samsung.com:device:RemoteControlReceiver:1\r\n\r\n"
    )
    headers = parse_response(raw)
    assert headers["location"] == "http://192.168.1.134:7676/rcr/"
    assert headers["server"].startswith("SHP")


def test_classifies_the_os_from_the_manufacturer() -> None:
    assert classify("Samsung Electronics", "QE55Q80", "") == "samsung"
    assert classify("LG Electronics", "OLED55C3", "WebOS/1.5") == "webos"
    assert classify("Amazon", "AFTKA", "") == "firetv"
    assert classify("Sony", "BRAVIA 4K", "Linux/4.9 UPnP/1.0") == "androidtv"
    assert classify("Sonos, Inc.", "Play:1", "Linux UPnP/1.0") is None
    assert classify("Google", "Eureka Dongle", "") is None  # cast-only Chromecast
