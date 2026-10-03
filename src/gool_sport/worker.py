from __future__ import annotations
import json,os,threading,time
from collections import defaultdict,deque
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from .brain import detect_signal,market_metric
from .config import SPORTS,env_int,sport_enabled
from .flashscore import Flashscore
from .journal import already_seen,load,save,settle
from .matching import map_events
from .telegram import CommandPoller,send,signal_message
from .xbet import XBet,balanced_total,clock_seconds,period,score

class SportWorker:
    def __init__(self,runtime=None):
        self.runtime=runtime or Path(os.getenv("RUNTIME_DATA_DIR","data"));live=self.runtime/"live";self.state_path=live/"state.json";self.history_path=live/"market_memory.jsonl";self.journal_path=live/"signals.json";self.flash=Flashscore();self.xbet=XBet();self.history=defaultdict(lambda:deque(maxlen=50));self.last_score={};self.score_changed_at={};self.last_period={};self.stop_event=threading.Event();self.poller=CommandPoller(self.journal_path,self.state_path);self._restore_history()
    def stop(self):self.stop_event.set()
    def _restore_history(self):
        try:
            size=self.history_path.stat().st_size
            with self.history_path.open("rb") as fh:
                fh.seek(max(0,size-4*1024*1024));data=fh.read()
            if size>4*1024*1024 and b"\n" in data:data=data.split(b"\n",1)[1]
        except FileNotFoundError:
            return
        restored=0
        for raw in data.splitlines():
            try:state=json.loads(raw.decode("utf-8"))
            except Exception:continue
            for key,cfg in SPORTS.items():
                for row in ((state.get("sports") or {}).get(key) or {}).get("matches") or []:
                    if not isinstance(row,dict) or not row.get("event_id") or row.get("ts") is None:continue
                    self._append(row,cfg);restored+=1
        if restored:print(f"GOOL_SPORT_MEMORY restored_snapshots={restored}",flush=True)
    def _snapshot(self,cfg,xrow,fs,rev,map_score):
        event_id=str(xrow.get("I") or "");game=xrow;total=balanced_total(game);xs=score(game)
        if total is None or xs is None:game=self.xbet.game(cfg.key,event_id) or {};total=balanced_total(game);xs=score(game)
        if total is None or xs is None:
            reason = "market_decode"
            if total is None and xs is None: reason = "market_and_score_decode"
            elif total is None: reason = "market_decode"
            else: reason = "score_decode"
            return None, f"{reason}|{fs.home}--{fs.away}|event={event_id}"
        canonical=(xs[1],xs[0]) if rev else xs;fs_score=(fs.home_score,fs.away_score)
        if canonical!=fs_score:
            return None, f"score_mismatch|{fs.home}--{fs.away}|fs={fs_score[0]}:{fs_score[1]}|xbet={canonical[0]}:{canonical[1]}|event={event_id}"
        now=time.time();return {"ts":now,"captured_at":datetime.now(timezone.utc).isoformat(),"sport":cfg.key,"event_id":event_id,"flashscore_event_id":fs.event_id,"home":fs.home,"away":fs.away,"league":fs.league,"score":[*fs_score],"period":period(game),"clock_seconds":clock_seconds(game),"line":float(total["line"]),"over":float(total["over"]),"under":float(total["under"]),"probability":float(total["probability"]),"metric":market_metric(total,fs_score,cfg),"mapping_score":round(float(map_score),4)},None
    def _append(self,row,cfg):
        key=f"{cfg.key}:{row['event_id']}";sc=tuple(row["score"]);per=str(row["period"])
        if self.last_period.get(key) not in {None,per}:self.history[key].clear()
        self.last_period[key]=per;prev=self.last_score.get(key)
        if prev is not None and prev!=sc:
            self.score_changed_at[key]=float(row["ts"])
            if cfg.key=="hockey":self.history[key].clear()
        self.last_score[key]=sc;self.history[key].append(dict(row));return list(self.history[key]),self.score_changed_at.get(key)
    def _record_signal(self,row,sig,cfg):
        rows=load(self.journal_path)
        if already_seen(rows,cfg.key,str(row["event_id"])):return False
        mode=str(os.getenv("GOOL_SPORT_MODE","shadow")).strip().casefold();entry={"entry_id":f"{cfg.key}:{row['event_id']}","created_at":datetime.now(timezone.utc).isoformat(),"sport":cfg.key,"event_id":row["event_id"],"flashscore_event_id":row["flashscore_event_id"],"home":row["home"],"away":row["away"],"league":row["league"],"score":list(row["score"]),"period":row["period"],"clock_seconds":row["clock_seconds"],"direction":sig.direction,"line":sig.line,"odd":sig.odd,"fair_probability":sig.fair_probability,"metric_delta":sig.metric_delta,"probability_delta_pp":sig.probability_delta_pp,"line_delta":sig.line_delta,"moves":sig.moves,"strength":sig.strength,"extreme":sig.extreme,"result":"pending","profit_units":0.0,"mode":mode,"telegram_sent":False}
        if mode=="active":entry["telegram_sent"]=bool(send(signal_message(entry)))
        rows.append(entry);save(self.journal_path,rows);print(f"GOOL_SPORT_SIGNAL sport={cfg.key} match={row['home']}--{row['away']} selection={sig.direction}:{sig.line:g} odd={sig.odd:.2f} strength={sig.strength:.0f} mode={mode}",flush=True);return True
    def _scan(self,cfg):
        fs_today=self.flash.today(cfg.flashscore_id);states={row.event_id:row for row in fs_today};rows=load(self.journal_path);changed=settle(rows,states)
        if changed:save(self.journal_path,rows)
        fs_live=[row for row in fs_today if row.is_live];xlive=self.xbet.index(cfg.key,cfg.xbet_id);mapped=map_events(xlive,fs_live)[:max(1,env_int("GOOL_SPORT_MAX_MAPPED_PER_SPORT",120))];decoded=mismatch=failed=detected=0;latest=[];diagnostics=[];workers=max(2,min(16,env_int("GOOL_SPORT_GAME_WORKERS",8)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs=[pool.submit(self._snapshot,cfg,xr,fs,rev,ms) for xr,fs,rev,ms in mapped]
            for future in as_completed(jobs):
                try:row,err=future.result(timeout=18)
                except Exception:row,err=None,"market_decode"
                if row is None:
                    err=str(err or "unknown")
                    is_mismatch=err.startswith("score_mismatch")
                    mismatch+=int(is_mismatch);failed+=int(not is_mismatch)
                    if len(diagnostics)<6:diagnostics.append(err)
                    continue
                decoded+=1;hist,changed_at=self._append(row,cfg);sig=detect_signal(hist,cfg,now=float(row["ts"]),score_changed_at=changed_at)
                if sig is not None:detected+=int(self._record_signal(row,sig,cfg));row["signal"]=sig.to_dict()
                latest.append(row)
        return {"enabled":True,"flashscore_live":len(fs_live),"xbet_live":len(xlive),"mapped":len(mapped),"decoded":decoded,"score_mismatch":mismatch,"market_decode_failed":failed,"detected":detected,"diagnostics":diagnostics,"matches":latest[:80]}
    def collect_once(self):
        started=time.time();sports={}
        for key,cfg in SPORTS.items():
            if not sport_enabled(key):sports[key]={"enabled":False};continue
            sports[key]=self._scan(cfg);row=sports[key];print(f"GOOL_{key.upper()} fs={row['flashscore_live']} xbet={row['xbet_live']} mapped={row['mapped']} decoded={row['decoded']} mismatch={row['score_mismatch']} decode_fail={row['market_decode_failed']} signals={row['detected']}",flush=True)
            if row["diagnostics"]:
                print(f"GOOL_{key.upper()}_DIAG "+" || ".join(row["diagnostics"][:3]),flush=True)
        state={"captured_at":datetime.now(timezone.utc).isoformat(),"latency_ms":int((time.time()-started)*1000),"mode":os.getenv("GOOL_SPORT_MODE","shadow"),"sports":sports};self.state_path.parent.mkdir(parents=True,exist_ok=True);tmp=self.state_path.with_suffix(".tmp");tmp.write_text(json.dumps(state,ensure_ascii=False,separators=(",",":")),"utf-8");tmp.replace(self.state_path)
        with self.history_path.open("a",encoding="utf-8") as fh:fh.write(json.dumps(state,ensure_ascii=False,separators=(",",":"))+"\n")
        self._trim_history();return state
    def _trim_history(self):
        keep=max(1024*1024,env_int("GOOL_SPORT_HISTORY_KEEP_BYTES",8*1024*1024))
        try:size=self.history_path.stat().st_size
        except FileNotFoundError:return
        if size<=keep:return
        with self.history_path.open("rb") as fh:fh.seek(max(0,size-keep));data=fh.read()
        if b"\n" in data:data=data.split(b"\n",1)[1]
        self.history_path.write_bytes(data)
    def run(self,interval):
        print(f"GOOL_SPORT started mode={os.getenv('GOOL_SPORT_MODE','shadow')} interval={interval:g}s sports=basketball,hockey fs_whitelist=required score_sync=required",flush=True)
        while not self.stop_event.is_set():
            started=time.monotonic()
            try:self.collect_once()
            except Exception as exc:print(f"GOOL_SPORT_ERROR {type(exc).__name__}:{exc}",flush=True)
            try:self.poller.poll_once()
            except Exception as exc:print(f"GOOL_SPORT_TELEGRAM_ERROR {type(exc).__name__}:{exc}",flush=True)
            self.stop_event.wait(max(1.0,interval-(time.monotonic()-started)))
