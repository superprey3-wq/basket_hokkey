from gool_sport.flashscore import FlashEvent
from gool_sport.journal import settle

def test_settle_over_and_under():
    states={"A":FlashEvent("A","H","A","L",4,3,"3","")}
    rows=[{"flashscore_event_id":"A","line":6.5,"direction":"over","odd":1.8,"result":"pending"},{"flashscore_event_id":"A","line":7.5,"direction":"under","odd":1.7,"result":"pending"}]
    assert settle(rows,states)==2
    assert rows[0]["result"]=="won" and rows[1]["result"]=="won"
