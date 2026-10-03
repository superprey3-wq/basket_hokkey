from __future__ import annotations
from dataclasses import asdict,dataclass
from typing import Any
from .config import SportConfig,env_float

@dataclass(frozen=True)
class Signal:
    direction:str;line:float;odd:float;fair_probability:float;metric_delta:float;probability_delta_pp:float;line_delta:float;moves:int;age_seconds:float;extreme:bool;strength:float
    def to_dict(self)->dict[str,Any]:return asdict(self)

def market_metric(total,score,cfg):
    current=int(score[0])+int(score[1]);remaining=float(total["line"])-current;bias=(float(total["probability"])-.5)*cfg.probability_scale
    return remaining+bias

def _moves(rows,direction,eps):
    count=0
    for left,right in zip(rows,rows[1:]):
        delta=float(right["metric"])-float(left["metric"])
        if (direction=="over" and delta>=eps) or (direction=="under" and delta<=-eps):count+=1
    return count

def detect_signal(rows,cfg,*,now,score_changed_at):
    eligible=[row for row in rows if now-float(row["ts"])<=cfg.window_seconds]
    if len(eligible)<max(4,cfg.min_moves+1):return None
    age=float(eligible[-1]["ts"])-float(eligible[0]["ts"])
    if age<cfg.min_age_seconds:return None
    if score_changed_at is not None and now-score_changed_at<cfg.score_guard_seconds:return None
    start,end=eligible[0],eligible[-1];raw=float(end["metric"])-float(start["metric"]);direction="over" if raw>0 else "under";delta=abs(raw)
    moves=_moves(eligible,direction,cfg.move_epsilon);extreme=delta>=cfg.extreme_metric_delta
    if delta<cfg.min_metric_delta or (moves<cfg.min_moves and not extreme):return None
    odd=float(end[direction]);min_odd=env_float("GOOL_SPORT_MIN_ODD",1.45);max_odd=env_float("GOOL_SPORT_MAX_ODD",3.25)
    if not(min_odd<=odd<=max_odd):return None
    over_p=float(end["probability"]);fair_p=over_p if direction=="over" else 1-over_p
    edge_proxy=abs((float(end["probability"])-float(start["probability"]))*100)
    if edge_proxy<env_float("GOOL_SPORT_MIN_FAIR_EDGE_PP",3.0) and not extreme:return None
    line_delta=float(end["line"])-float(start["line"]);prob_delta=(float(end["probability"])-float(start["probability"]))*100
    if direction=="under":prob_delta=-prob_delta;line_delta=-line_delta
    strength=min(100.0,58+delta/max(1e-6,cfg.min_metric_delta)*13+moves*3+(7 if extreme else 0))
    return Signal(direction,float(end["line"]),odd,fair_p,delta,prob_delta,line_delta,moves,age,extreme,round(strength,1))
