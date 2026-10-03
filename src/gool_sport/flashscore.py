from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
from .http import UA,get_text

FSIGN=os.getenv("FLASHSCORE_FSIGN","SW9D1eZo")
BASES=("https://local-global.flashscore.ninja/2/x/feed","https://global.flashscore.ninja/2/x/feed","https://2.flashscore.ninja/2/x/feed")

def _fields(raw:str)->dict[str,str]:
    out={}
    for token in raw.split("¬"):
        if "÷" in token:
            key,value=token.split("÷",1)
            if key and key not in out:
                out[key]=value
    return out

def _int(value:Any,default:int=0)->int:
    try:return int(float(str(value)))
    except (TypeError,ValueError):return default

@dataclass(frozen=True)
class FlashEvent:
    event_id:str
    home:str
    away:str
    league:str
    home_score:int
    away_score:int
    coarse_status:str
    status_code:str
    @property
    def is_live(self)->bool:return self.coarse_status=="2"
    @property
    def is_finished(self)->bool:return self.coarse_status=="3"

class Flashscore:
    def _feed(self,path:str)->str:
        headers={"User-Agent":UA,"x-fsign":FSIGN,"Origin":"https://www.flashscore.com","Referer":"https://www.flashscore.com/","Accept":"*/*","Cache-Control":"no-cache"}
        for base in BASES:
            body=get_text(f"{base}/{path}",headers=headers,timeout=8)
            if body and not body.lstrip().lower().startswith("<"):
                return body
        return ""
    @staticmethod
    def parse(body:str)->list[FlashEvent]:
        league="";rows={}
        for chunk in (body or "").split("~"):
            if not chunk:continue
            if chunk.startswith("ZA÷"):
                league=str(_fields(chunk).get("ZA") or "").strip();continue
            if not chunk.startswith("AA÷"):continue
            event_id,sep,rest=chunk[3:].partition("¬")
            if not sep or len(event_id)!=8 or not event_id.isalnum():continue
            f=_fields(rest);home=str(f.get("AE") or f.get("CX") or "").strip();away=str(f.get("AF") or "").strip()
            if not home or not away:continue
            rows[event_id]=FlashEvent(event_id,home,away,league,_int(f.get("AG"),_int(f.get("AT"))),_int(f.get("AH"),_int(f.get("AU"))),str(f.get("AB") or ""),str(f.get("AC") or ""))
        return list(rows.values())
    def today(self,sport_id:int)->list[FlashEvent]:
        merged={}
        for path in (f"f_{sport_id}_0_3_en_1",f"f_{sport_id}_0_0_en_1"):
            for row in self.parse(self._feed(path)):
                merged[row.event_id]=row
        return list(merged.values())
