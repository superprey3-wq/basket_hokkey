from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from .flashscore import FlashEvent

FINAL={"won","lost","void"}

def load(path):
    try:
        value=json.loads(path.read_text("utf-8"));return value if isinstance(value,list) else []
    except Exception:return []

def save(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(rows,ensure_ascii=False,separators=(",",":")),"utf-8");tmp.replace(path)

def already_seen(rows,sport,event_id):
    return any(str(row.get("sport"))==sport and str(row.get("event_id"))==event_id for row in rows)

def settle(rows,states):
    changed=0
    for row in rows:
        if str(row.get("result") or "pending") in FINAL:continue
        fs=states.get(str(row.get("flashscore_event_id") or ""))
        if fs is None or not fs.is_finished:continue
        total=fs.home_score+fs.away_score;line=float(row["line"]);direction=str(row["direction"])
        if total==line:result="void";profit=0.0
        else:
            won=total>line if direction=="over" else total<line;result="won" if won else "lost";profit=float(row["odd"])-1 if won else -1.0
        row.update({"result":result,"profit_units":round(profit,4),"settled_at":datetime.now(timezone.utc).isoformat(),"settled_score":[fs.home_score,fs.away_score]});changed+=1
    return changed

def report(rows):
    settled=[r for r in rows if r.get("result") in FINAL];won=sum(1 for r in settled if r.get("result")=="won");lost=sum(1 for r in settled if r.get("result")=="lost");pending=sum(1 for r in rows if r.get("result")=="pending");profit=sum(float(r.get("profit_units") or 0) for r in settled);roi=profit/len(settled)*100 if settled else 0
    parts=[]
    for sport,icon in (("basketball","🏀"),("hockey","🏒")):
        xs=[r for r in settled if r.get("sport")==sport]
        if xs:
            sw=sum(1 for r in xs if r.get("result")=="won");sp=sum(float(r.get("profit_units") or 0) for r in xs);parts.append(f"{icon} {len(xs)} · ✅ {sw} · ❌ {len(xs)-sw} · P/L {sp:+.2f}u")
    return "📊 <b>GOOL SPORT · SHADOW REPORT</b>\n\n"+f"Всего: <b>{len(rows)}</b> · рассчитано: <b>{len(settled)}</b> · ⏳ {pending}\n✅ {won} · ❌ {lost} · проход {(won/len(settled)*100 if settled else 0):.1f}%\nP/L <b>{profit:+.2f}u</b> · ROI <b>{roi:+.1f}%</b>"+(("\n\n"+"\n".join(parts)) if parts else "")
