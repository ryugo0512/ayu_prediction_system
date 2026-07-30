import json
import os
import re
import datetime
import requests

DATA_DIR = "data"
WATER_LEVELS_FILE = os.path.join(DATA_DIR, "water_levels.json")
PARAMS_FILE = os.path.join(DATA_DIR, "river_params.json")

RIVERS = {
    "尻別川本流": {"url": "https://weathernews.jp/onebox/river/shiribetsugawa/?pid=2078700400004", "default_level": 9.08},
    "昆布川": {"url": "https://weathernews.jp/onebox/river/shiribetsugawa/?pid=0025700400389", "default_level": 43.58},
    "天ノ川": {"url": "https://weathernews.jp/onebox/river/?pid=0025700400132", "default_level": 1.60},
    "朱太川": {"url": "https://weathernews.jp/onebox/river/shubutogawa/?pid=0025700400387", "default_level": 1.44}
}

LOCATIONS = {
    "rankoshi": {"lat": 42.79, "lon": 140.47},
    "niseko": {"lat": 42.80, "lon": 140.68},
    "kutchan": {"lat": 42.90, "lon": 140.76},
    "kimobetsu": {"lat": 42.79, "lon": 140.92}
}

def fetch_water_level(url, default_val):
    if not url: return default_val, True
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        clean_text = " ".join(re.sub(r"<[^>]+>", " ", res.text).split())
        for pat in [r"現在水位\s*(\d+\.\d{2})\s*m", r"\d{1,2}:\d{2}\s*時点\s*(\d+\.\d{2})\s*m", r"時点\s*(\d+\.\d{2})\s*m"]:
            match = re.search(pat, clean_text)
            if match:
                val = float(match.group(1))
                if abs(val - default_val) <= 2.0: return val, False
        matches = re.findall(r"(\d+\.\d{2})\s*m", clean_text)
        if matches:
            for m_str in matches:
                val = float(m_str)
                if abs(val - default_val) <= 2.0: return val, False
        return default_val, True
    except Exception:
        return default_val, True

def fetch_current_rain():
    rain_data = {}
    for loc_name, coords in LOCATIONS.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current=precipitation&timezone=Asia%2FTokyo"
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()
            rain_data[loc_name] = data.get("current", {}).get("precipitation", 0.0)
        except Exception:
            rain_data[loc_name] = 0.0
    return rain_data

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(WATER_LEVELS_FILE):
        try:
            with open(WATER_LEVELS_FILE, "r", encoding="utf-8") as f:
                water_levels = json.load(f)
        except Exception:
            water_levels = {}
    else:
        water_levels = {}

    now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    current_rain = fetch_current_rain()

    for river_name, info in RIVERS.items():
        val, is_error = fetch_water_level(info["url"], info["default_level"])
        if river_name not in water_levels:
            water_levels[river_name] = []
        
        new_record = {
            "timestamp": now_str,
            "water_level": val,
            "fetch_error": is_error,
            "rain_rankoshi": current_rain.get("rankoshi", 0.0),
            "rain_niseko": current_rain.get("niseko", 0.0),
            "rain_kutchan": current_rain.get("kutchan", 0.0),
            "rain_kimobetsu": current_rain.get("kimobetsu", 0.0)
        }
        water_levels[river_name].append(new_record)
        water_levels[river_name] = water_levels[river_name][-336:]

    with open(WATER_LEVELS_FILE, "w", encoding="utf-8") as f:
        json.dump(water_levels, f, ensure_ascii=False, indent=2)
    
    with open(PARAMS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
