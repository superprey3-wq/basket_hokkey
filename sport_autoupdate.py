from __future__ import annotations
import io,os,shutil,sys,urllib.request,zipfile
from pathlib import Path

ROOT=Path("/home/container");DEPLOY=ROOT/"gool_sport_deploy";ZIP_URL="https://github.com/superprey3-wq/basket_hokkey/archive/refs/heads/main.zip"

def main():
    print("GOOL_SPORT_UPDATE downloading main",flush=True)
    with urllib.request.urlopen(ZIP_URL,timeout=30) as response:data=response.read()
    temp=ROOT/".gool_sport_new";shutil.rmtree(temp,ignore_errors=True);temp.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:archive.extractall(temp)
    roots=[p for p in temp.iterdir() if p.is_dir()]
    if len(roots)!=1:raise RuntimeError("unexpected_archive_layout")
    shutil.rmtree(DEPLOY,ignore_errors=True);roots[0].replace(DEPLOY);shutil.rmtree(temp,ignore_errors=True)
    env=os.environ.copy();env["PYTHONPATH"]=str(DEPLOY/"src");print(f"GOOL_SPORT_UPDATE ready deploy={DEPLOY}",flush=True);os.execve(sys.executable,[sys.executable,"-m","gool_sport"],env)

if __name__=="__main__":main()
