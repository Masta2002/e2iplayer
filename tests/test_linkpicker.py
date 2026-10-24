# Offline tests for the automatic link choice: IPTVPlayer/tools/linkpicker.py (height read from a link name,
# the quality closest to "Default video quality", the order "Select link automatically" tries mirrors in).
# The module has no enigma2 / E2iPlayer imports.
import importlib.util
import os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "IPTVPlayer")


def _load():
    spec = importlib.util.spec_from_file_location("linkpicker_under_test", os.path.join(ROOT, "tools", "linkpicker.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lp = _load()


class Link(object):
    def __init__(self, name, failed=False):
        self.name = name
        self.failed = failed


def _names(links):
    return [link.name for link in links]


def test_link_height_formats():
    assert lp.linkHeight("720p") == 720
    assert lp.linkHeight("[HLS] 1080p") == 1080
    assert lp.linkHeight("bitrate: 2500000 res: 1280x720") == 720
    assert lp.linkHeight("[ar] bitrate: 800000 640x360 avc1 25fps") == 360
    assert lp.linkHeight("mp4 4K") == 2160
    assert lp.linkHeight("FHD") == 1080
    assert lp.linkHeight("1080i") == 1080


def test_link_height_none():
    assert lp.linkHeight("Vidoza") == 0
    assert lp.linkHeight("bitrate: 128000 audio only") == 0
    assert lp.linkHeight("[f4m/hds] bitrate[1500]") == 0
    assert lp.linkHeight("Server 2024") == 0
    assert lp.linkHeight("") == 0
    assert lp.linkHeight(None) == 0


def test_pick_closest_not_above_wish():
    links = [Link("1080p"), Link("720p"), Link("480p")]
    assert lp.pickByQuality(links, "720").name == "720p"
    assert lp.pickByQuality(links, "2160").name == "1080p"
    assert lp.pickByQuality(links, "max").name == "1080p"
    # nothing at or below the wish: the lowest one
    assert lp.pickByQuality(links, "360").name == "480p"


def test_pick_ask_or_no_quality_list():
    links = [Link("1080p"), Link("720p")]
    assert lp.pickByQuality(links, "") is None
    # a mirror list (not every link names a height): the picker stays
    assert lp.pickByQuality([Link("Vidoza 720p"), Link("Streamtape")], "720") is None
    assert lp.pickByQuality([Link("720p")], "720") is None


def test_pick_ignores_audio_only():
    links = [Link("bitrate: 128000 audio only"), Link("res: 1920x1080"), Link("res: 1280x720")]
    assert lp.pickByQuality(links, "720").name == "res: 1280x720"


def test_auto_order_preferred_first_then_host_order():
    links = [Link("Vidoza"), Link("Dood 480p"), Link("VOE 720p"), Link("Streamtape 720p")]
    assert _names(lp.autoOrder(links, "720", lambda link: link.failed)) == ["VOE 720p", "Streamtape 720p", "Vidoza", "Dood 480p"]
    assert _names(lp.autoOrder(links, "", lambda link: link.failed)) == _names(links)


def test_auto_order_skips_failed_unless_all_failed():
    links = [Link("A", failed=True), Link("B"), Link("C")]
    assert _names(lp.autoOrder(links, "", lambda link: link.failed)) == ["B", "C"]
    allFailed = [Link("A", failed=True), Link("B", failed=True)]
    assert _names(lp.autoOrder(allFailed, "", lambda link: link.failed)) == ["A", "B"]
