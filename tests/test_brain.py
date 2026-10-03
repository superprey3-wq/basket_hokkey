from gool_sport.brain import detect_signal
from gool_sport.config import SPORTS

def rows(direction="over"):
    base=[{"ts":0,"metric":10.0,"line":210.5,"over":1.90,"under":1.90,"probability":.50},{"ts":10,"metric":11.2,"line":211.5,"over":1.82,"under":2.00,"probability":.52},{"ts":20,"metric":12.5,"line":212.5,"over":1.75,"under":2.10,"probability":.545},{"ts":30,"metric":14.2,"line":214.5,"over":1.65,"under":2.25,"probability":.58}]
    if direction=="under":return [{**r,"metric":24-r["metric"],"over":r["under"],"under":r["over"],"probability":1-r["probability"]} for r in base]
    return base

def test_basketball_over_steam():
    sig=detect_signal(rows(),SPORTS["basketball"],now=30,score_changed_at=None)
    assert sig is not None and sig.direction=="over"

def test_basketball_under_steam():
    sig=detect_signal(rows("under"),SPORTS["basketball"],now=30,score_changed_at=None)
    assert sig is not None and sig.direction=="under"

def test_score_guard_blocks_fresh_score():
    assert detect_signal(rows(),SPORTS["basketball"],now=30,score_changed_at=28) is None
