from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import Any
from .flashscore import FlashEvent

EXCLUDED=("esports","e-sports","cyber","virtual","ebasketball","ehockey","nba2k","2x2","3x3")

def norm(name:str)->str:
    value=str(name or "").casefold()
    value=re.sub(r"\([^)]*\)"," ",value)
    value=re.sub(r"[^a-z0-9а-яё]+"," ",value)
    return " ".join(value.split())

def similarity(a:str,b:str)->float:
    na,nb=norm(a),norm(b)
    if not na or not nb:return 0.0
    if na==nb:return 1.0
    return SequenceMatcher(None,na,nb).ratio()

def allowed_xbet(event:dict[str,Any])->bool:
    text=" ".join(str(event.get(k) or "") for k in ("L","LE","SN","O1","O2")).casefold()
    return not any(marker in text for marker in EXCLUDED)

def map_events(xbet_events:list[dict[str,Any]],flash_events:list[FlashEvent],*,min_score:float=.70,min_side:float=.52):
    candidates=[]
    for xi,xbet in enumerate(xbet_events):
        if not allowed_xbet(xbet):continue
        xh,xa=str(xbet.get("O1") or ""),str(xbet.get("O2") or "")
        for fi,fs in enumerate(flash_events):
            direct_sides=(similarity(xh,fs.home),similarity(xa,fs.away))
            reverse_sides=(similarity(xh,fs.away),similarity(xa,fs.home))
            direct=sum(direct_sides)/2;reverse=sum(reverse_sides)/2
            rev=reverse>direct;score=reverse if rev else direct;weakest=min(reverse_sides if rev else direct_sides)
            if score>=min_score and weakest>=min_side:candidates.append((score,xi,fi,rev))
    candidates.sort(reverse=True);used_x=set();used_f=set();out=[]
    for score,xi,fi,rev in candidates:
        if xi in used_x or fi in used_f:continue
        used_x.add(xi);used_f.add(fi);out.append((xbet_events[xi],flash_events[fi],rev,score))
    return out
