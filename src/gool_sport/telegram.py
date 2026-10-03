from __future__ import annotations
import json,os,urllib.request
from .journal import load,report

def _token():return os.getenv("TELEGRAM_BOT_TOKEN","").strip()
def _chat_id():return os.getenv("TELEGRAM_CHAT_ID","").strip()

def api(method,payload,timeout=8):
    token=_token()
    if not token:return None
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            value=json.loads(response.read().decode());return value if isinstance(value,dict) else None
    except Exception:return None

def send(text,chat_id=None):
    cid=str(chat_id or _chat_id())
    if not cid:return 0
    value=api("sendMessage",{"chat_id":cid,"text":text,"parse_mode":"HTML","disable_web_page_preview":True});return int(bool(value and value.get("ok")))

def signal_message(row):
    icon="🏀" if row["sport"]=="basketball" else "🏒";arrow="⬆️" if row["direction"]=="over" else "⬇️";market=f"ТБ {float(row['line']):g}" if row["direction"]=="over" else f"ТМ {float(row['line']):g}";score=row.get("score") or [0,0];mode=str(row.get("mode") or "shadow").upper()
    return f"{icon} <b>GOOL SPORT · {mode}</b>\n<b>{row['home']} — {row['away']}</b> · {score[0]}:{score[1]}\n🏆 {row.get('league') or 'LIVE'}\n{arrow} <b>{market} @ {float(row['odd']):.2f}</b>\n🧠 сила {float(row['strength']):.0f}/100 · движение {float(row['metric_delta']):.2f}\n📈 Δp {float(row['probability_delta_pp']):+.1f}пп · импульсов {int(row['moves'])}"

class CommandPoller:
    def __init__(self,journal_path,state_path):self.offset=0;self.journal_path=journal_path;self.state_path=state_path
    def _status(self):
        try:state=json.loads(self.state_path.read_text("utf-8"))
        except Exception:state={}
        sports=state.get("sports") or {};lines=["🧠 <b>GOOL SPORT · STATUS</b>"]
        for key,icon in (("basketball","🏀"),("hockey","🏒")):
            row=sports.get(key) or {}
            lines.append(f"{icon} выключен" if row.get("enabled") is False else f"{icon} FS {row.get('flashscore_live',0)} · 1xBet {row.get('xbet_live',0)} · mapped {row.get('mapped',0)} · decoded {row.get('decoded',0)} · mismatch {row.get('score_mismatch',0)} · decode_fail {row.get('market_decode_failed',0)}")
        lines.append(f"Режим: <b>{os.getenv('GOOL_SPORT_MODE','shadow').upper()}</b>");return "\n".join(lines)
    def poll_once(self):
        if not _token():return
        value=api("getUpdates",{"offset":self.offset,"timeout":0,"allowed_updates":["message"]},timeout=4)
        if not value or not value.get("ok"):return
        for update in value.get("result") or []:
            self.offset=max(self.offset,int(update.get("update_id") or 0)+1);message=update.get("message") or {};text=str(message.get("text") or "").split("@",1)[0].strip().lower();cid=str((message.get("chat") or {}).get("id") or "")
            if not cid:continue
            allowed=_chat_id()
            if allowed and cid!=allowed:continue
            if text in {"/start","/help"}:send("🏀🏒 <b>GOOL SPORT</b>\n\n/status — источники\n/in_game — что сейчас отслеживается\n/report — shadow результаты\n/help — команды",cid)
            elif text=="/status":send(self._status(),cid)
            elif text=="/report":send(report(load(self.journal_path)),cid)
            elif text=="/in_game":
                try:state=json.loads(self.state_path.read_text("utf-8"))
                except Exception:state={}
                lines=["🟢 <b>GOOL SPORT · В ИГРЕ</b>"]
                shown=0
                for key,icon in (("basketball","🏀"),("hockey","🏒")):
                    for row in (((state.get("sports") or {}).get(key) or {}).get("matches") or []):
                        score=row.get("score") or [0,0];period=str(row.get("period") or "LIVE");line=float(row.get("line") or 0);over=float(row.get("over") or 0);under=float(row.get("under") or 0)
                        lines.append(f"{icon} <b>{row.get('home','?')} — {row.get('away','?')}</b> · {score[0]}:{score[1]} · {period}\n↳ линия {line:g} · ТБ {over:.2f} / ТМ {under:.2f}")
                        shown+=1
                        if shown>=8:break
                    if shown>=8:break
                if shown==0:lines.append("Сейчас нет синхронизированных LIVE-матчей.")
                send("\n\n".join(lines),cid)
