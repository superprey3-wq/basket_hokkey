from __future__ import annotations
import os,signal
from pathlib import Path
from .config import env_float
from .worker import SportWorker

def _load_env(path):
    if not path.exists():return
    for raw in path.read_text("utf-8").splitlines():
        line=raw.strip()
        if not line or line.startswith("#") or "=" not in line:continue
        key,value=line.split("=",1);os.environ.setdefault(key.strip(),value.strip())

def main():
    _load_env(Path(os.getenv("GOOL_SPORT_ENV_FILE","/home/container/sport.env")));runtime=Path(os.getenv("RUNTIME_DATA_DIR","/home/container/gool_sport_data"));os.environ["RUNTIME_DATA_DIR"]=str(runtime);worker=SportWorker(runtime);signal.signal(signal.SIGINT,lambda *_:worker.stop());signal.signal(signal.SIGTERM,lambda *_:worker.stop());worker.run(max(8.0,env_float("GOOL_SPORT_INTERVAL_SECONDS",20.0)))

if __name__=="__main__":main()
