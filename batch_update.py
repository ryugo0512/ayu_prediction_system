import json
import os
import re
import datetime
import requests
import numpy as np
import pandas as pd

DATA_DIR = "data"
WATER_LEVELS_FILE = os.path.join(DATA_DIR, "water_levels.json")
PARAMS_FILE = os.path.join(DATA_DIR, "river_params.json")

RIVERS = {
    "尻別川本流": {
        "url": "https://weathernews.jp/onebox/river/shiribetsugawa/?pid=2078700400004",
        "default_level": 9.08,
        "base_level": 9.08,
        "decay_rate": 0.9975
    },
    "昆布川": {
        "url": "https://weathernews.jp/onebox/river/shiribetsugawa/?pid=0025700400389",
        "default_level": 43.58,
        "base_level": 43.58,
        "decay_rate": 0.9970
    },
    "天ノ川": {
        "url": "https://weathernews.jp/onebox/river/?pid=0025700400132",
        "default_level": 1.60,
        "base_level": 1.60,
        "decay_rate": 0.9975
    },
    "朱太川": {
        "url": "https://weathernews.jp/onebox/river/shubutogawa/?pid=0025700400387",
        "default_level": 1.44,
        "base_level": 1.44,
        "decay_rate": 0.9972
    }
}

def fetch_water_level(url, default_val):
    if not url:
        return default_val, True
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        clean_text = " ".join(re.sub(r"<[^>]+>", " ", res.text).split())
        
        for pat in [r"現在水位\s*(\d+\.\d{2})\s*m", r"\d{1,2}:\d{2}\s*時点\s*(\d+\.\d{2})\s*m", r"時点\s*(\d+\.\d{2})\s*m"]:
            match = re.search(pat, clean_text)
            if match:
                val = float(match.group(1))
                if abs(val - default_val) <= 2.0:
                    return val, False
                
        matches = re.findall(r"(\d+\.\d{2})\s*m", clean_text)
        if matches:
            for m_str in matches:
                val = float(m_str)
                if abs(val - default_val) <= 2.0:
                    return val, False
                    
        return default_val, True
    except Exception:
        return default_val, True

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 既存の蓄積データを読み込む（無ければ空の辞書）
    if os.path.exists(WATER_LEVELS_FILE):
        try:
            with open(WATER_LEVELS_FILE, "r", encoding="utf-8") as f:
                water_levels = json.load(f)
        except Exception:
            water_levels = {}
    else:
        water_levels = {}

    # 既存のパラメータを読み込む
    if os.path.exists(PARAMS_FILE):
        try:
            with open(PARAMS_FILE, "r", encoding="utf-8") as f:
                river_params = json.load(f)
        except Exception:
            river_params = {}
    else:
        river_params = {}

    now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")

    for river_name, info in RIVERS.items():
        val, is_error = fetch_water_level(info["url"], info["default_level"])
        
        if river_name not in water_levels:
            water_levels[river_name] = []
            
        # 履歴に追加（上書きせずにAppend）
        new_record = {
            "timestamp": now_str,
            "water_level": val,
            "fetch_error": is_error
        }
        water_levels[river_name].append(new_record)
        
        # 直近7日分（最大168件）のみ保持して古いデータを整理
        water_levels[river_name] = water_levels[river_name][-168:]

        # パラメータデータの更新
        if river_name not in river_params:
            river_params[river_name] = {}
            
        river_params[river_name]["decay_rate"] = info["decay_rate"]
        river_params[river_name]["base_level"] = info["base_level"]
        if not is_error:
            river_params[river_name]["last_valid_level"] = val
            river_params[river_name]["last_success_time"] = now_str

    # 追記保存
    with open(WATER_LEVELS_FILE, "w", encoding="utf-8") as f:
        json.dump(water_levels, f, ensure_ascii=False, indent=2)

    with open(PARAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(river_params, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
