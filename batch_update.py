import json
import os
from datetime import datetime
import requests
import re

DATA_DIR = "data"
PARAMS_FILE = os.path.join(DATA_DIR, "river_params.json")
WATER_LOG_FILE = "water_levels_history.json"  # 1つ目のプログラムと同じ保存先を指定

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_water_history():
    if os.path.exists(WATER_LOG_FILE):
        with open(WATER_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_water_history(river_name, timestamp_str, level):
    history = load_water_history()
    if river_name not in history:
        history[river_name] = {}
    history[river_name][timestamp_str] = level
    with open(WATER_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def fetch_water_level(url):
    """
    1つ目のプログラムと同様の正規表現を用いて実際の水位を取得する処理
    """
    if not url: 
        return None
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        clean_text = " ".join(re.sub(r"<[^>]+>", " ", res.text).split())
        
        extracted_val = None
        for pat in [r"現在水位\s*(\d+\.\d{2})\s*m", r"\d{1,2}:\d{2}\s*時点\s*(\d+\.\d{2})\s*m", r"時点\s*(\d+\.\d{2})\s*m"]:
            match = re.search(pat, clean_text)
            if match:
                extracted_val = float(match.group(1))
                break
        
        if extracted_val is None:
            matches = re.findall(r"(\d+\.\d{2})\s*m", clean_text)
            if matches:
                extracted_val = float(matches[0])
                
        return extracted_val
    except Exception as e:
        print(f"スクレイピングエラー ({url}): {e}")
        return None

def optimize_parameters(params, current_level):
    """
    河川別のパラメータ自動最適化（AI学習ロジック）
    実測値と基準値のズレを基に、減衰率や流出係数を±5%以内で微調整する
    """
    if current_level is None:
        return params

    base_level = params.get("base_level", 1.0)
    diff = current_level - base_level

    # ズレに応じたパラメータの微調整（変動幅は安全な上限±5%に制限）
    current_decay = params.get("decay_rate", 0.9975)
    if diff > 0.5:
        new_decay = max(current_decay * 0.99, current_decay * 0.95)
    else:
        new_decay = min(current_decay * 1.01, current_decay * 1.05)
    
    params["decay_rate"] = round(float(new_decay), 5)
    params["last_valid_level"] = current_level
    params["last_success_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return params

def main():
    params_data = load_json(PARAMS_FILE)
    if not params_data:
        print("パラメータファイルが見つかりません。")
        return

    # グラフ表示用に「YYYY-MM-DD HH:00」の形式で現在時刻を作成
    now_hour_str = datetime.now().strftime("%Y-%m-%d %H:00")

    for river_name, params in params_data.items():
        url = params.get("url")
        print(f"処理中: {river_name} (URL: {url})")
        
        # 水位データ取得
        current_level = fetch_water_level(url)
        
        # 取得に成功した場合、水位履歴ファイルへ保存する処理を追加
        if current_level is not None:
            save_water_history(river_name, now_hour_str, current_level)
            print(f"-> 水位 {current_level}m を履歴に保存しました。")
        
        # パラメータの自動最適化（学習）を実行
        updated_params = optimize_parameters(params, current_level)
        params_data[river_name] = updated_params

    # 更新されたパラメータと学習結果を保存
    save_json(params_data, PARAMS_FILE)
    print("すべての河川のパラメータ最適化とデータ更新が完了しました。")

if __name__ == "__main__":
    main()
