from gool_sport.flashscore import FlashEvent
from gool_sport.matching import map_events

def test_mapping_matches_names_and_reversal():
    fs=[FlashEvent("ABCDEFGH","Boston Celtics","LA Lakers","NBA",20,18,"2","")]
    x=[{"I":1,"O1":"Los Angeles Lakers","O2":"Boston Celtics"}]
    mapped=map_events(x,fs,min_score=.45,min_side=.35)
    assert len(mapped)==1
    assert mapped[0][2] is True
