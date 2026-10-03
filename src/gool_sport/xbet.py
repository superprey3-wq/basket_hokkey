from __future__ import annotations
import urllib.parse
from typing import Any
from .http import UA,get_json

ROOTS=("https://1xbet.com/service-api/LiveFeed","https://1xbet.com/LiveFeed","https://1xbet.fi/service-api/LiveFeed","https://1xbet.fi/LiveFeed")
HEADERS={"User-Agent":UA,"Accept":"application/json,*/*","Origin":"https://1xbet.com","Referer":"https://1xbet.com/live/","X-Requested-With":"XMLHttpRequest","is-srv":"false","x-app-n":"__BETTING_APP__","x-svc-source":"__BETTING_APP__","x-mobile-project-id":"0"}

def _nodes(obj:Any,out=None):
    out=[] if out is None else out
    if isinstance(obj,dict):
        if "T" in obj and "C" in obj:
            try:odd=float(obj.get("C"));typ=int(obj.get("T"));line=None if obj.get("P") is None else float(obj.get("P"))
            except (TypeError,ValueError):odd,typ,line=0.0,-1,None
            if odd>1.001 and typ>0:out.append({"T":typ,"C":odd,"P":line,"G":obj.get("G")})
        for value in obj.values():_nodes(value,out)
    elif isinstance(obj,list):
        for value in obj:_nodes(value,out)
    return out

def _pairs(nodes,group):
    grouped={}
    for node in nodes:
        if node.get("P") is None or int(node.get("G") or -1)!=group:continue
        typ=int(node.get("T") or -1)
        if typ not in {9,10}:continue
        line=float(node["P"]);row=grouped.setdefault(line,{"line":line});row["over" if typ==9 else "under"]=float(node["C"])
    return [grouped[key] for key in sorted(grouped)]

def decode_totals(game):
    nodes=_nodes(game)
    for group in (17,4):
        complete=[row for row in _pairs(nodes,group) if row.get("over") and row.get("under")]
        if complete:return complete
    return []

def fair_over(over,under):
    a,b=1/float(over),1/float(under);return a/(a+b)

def balanced_total(game):
    rows=[]
    for row in decode_totals(game):
        over,under=float(row["over"]),float(row["under"])
        if 1.08<=over<=8 and 1.08<=under<=8:rows.append({**row,"probability":fair_over(over,under)})
    return min(rows,key=lambda x:abs(float(x["probability"])-.5)) if rows else None

def score(game):
    sc=game.get("SC") or {};fs=sc.get("FS") or {}
    for root in (fs,game):
        try:
            if root.get("S1") is not None and root.get("S2") is not None:return int(float(root["S1"])),int(float(root["S2"]))
        except (TypeError,ValueError):pass
    return None

def period(game):
    sc=game.get("SC") or {};return str(sc.get("CPS") or sc.get("CP") or sc.get("I") or "LIVE").strip() or "LIVE"

def clock_seconds(game):
    try:
        raw=(game.get("SC") or {}).get("TS");return None if raw is None else max(0,int(float(raw)))
    except (TypeError,ValueError):return None

class XBet:
    def __init__(self):
        self.roots={}
        self.last_index_diag={}
    def index(self,sport_key,sport_id):
        queries=[
            urllib.parse.urlencode({"sports":sport_id,"count":1000,"lng":"en","mode":4,"country":1,"getEmpty":"true"}),
            urllib.parse.urlencode({"sports":sport_id,"count":1000,"lng":"en","mode":4,"country":137,"gr":285,"virtualSports":"true","noFilterBlockEvent":"true","getEmpty":"true"}),
        ]
        seen=set();attempts=[]
        for root in (self.roots.get(sport_key,ROOTS[0]),*ROOTS):
            if root in seen:continue
            seen.add(root)
            for qi,query in enumerate(queries,1):
                payload=get_json(f"{root}/Get1x2_VZip?{query}",headers=HEADERS,timeout=7)
                values=payload.get("Value") if isinstance(payload,dict) else None
                count=len(values) if isinstance(values,list) else 0
                attempts.append({"root":root,"query":qi,"count":count,"payload":bool(payload)})
                if isinstance(values,list) and values:
                    rows=[row for row in values if isinstance(row,dict) and row.get("I") and row.get("O1") and row.get("O2")]
                    if rows:
                        self.roots[sport_key]=root
                        self.last_index_diag[sport_key]={"ok":True,"root":root,"query":qi,"raw":count,"usable":len(rows),"attempts":attempts[-4:]}
                        return rows
        self.last_index_diag[sport_key]={"ok":False,"root":None,"query":None,"raw":0,"usable":0,"attempts":attempts[-8:]}
        return []
    def game(self,sport_key,event_id):
        query=urllib.parse.urlencode({"id":event_id,"lng":"en","cfview":0,"isSubGames":"true","GroupEvents":"true","allEventsGroupSubGames":"true","countevents":250,"grMode":2})
        seen=set()
        for root in (self.roots.get(sport_key,ROOTS[0]),*ROOTS):
            if root in seen:continue
            seen.add(root);payload=get_json(f"{root}/GetGameZip?{query}",headers=HEADERS,timeout=7);value=payload.get("Value") if isinstance(payload,dict) else None
            if isinstance(value,dict):self.roots[sport_key]=root;return value
        return None
