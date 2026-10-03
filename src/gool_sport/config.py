from __future__ import annotations
import os
from dataclasses import dataclass

def truthy(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().casefold() not in {"0", "false", "no", "off"}

def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)

@dataclass(frozen=True)
class SportConfig:
    key: str
    icon: str
    title: str
    flashscore_id: int
    xbet_id: int
    probability_scale: float
    min_metric_delta: float
    extreme_metric_delta: float
    min_moves: int
    min_age_seconds: float
    score_guard_seconds: float
    cooldown_seconds: float
    window_seconds: float
    move_epsilon: float

SPORTS = {
    "basketball": SportConfig("basketball","🏀","BASKETBALL",3,3,40.0,3.5,6.0,3,24.0,6.0,8*60.0,3*60.0,0.30),
    "hockey": SportConfig("hockey","🏒","HOCKEY",4,2,4.0,0.45,0.75,3,28.0,16.0,12*60.0,4*60.0,0.035),
}

def sport_enabled(key: str) -> bool:
    return truthy(f"GOOL_{key.upper()}_ENABLED", True)
