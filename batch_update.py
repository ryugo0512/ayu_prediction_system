import json
import os
from datetime import datetime, timedelta, timezone
import requests
import re

# 日本時間（JST）の設定
JST = timezone(timedelta(hours=+9), 'JST')

DATA_DIR = "data"
PARAMS_FILE = os.path.join(DATA_DIR, "river_params.json")
WATER_LOG_FILE = os.path.join(DATA_DIR, "water_levels.json")  # 修正: 正しい保存先を指定

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
        history[river_name] = []
    
    # リスト形式（app.pyが読み込むフォーマット）で追加
    history[river_name].append({
        "timestamp": timestamp_str,
        "water_level": level,
        "fetch_error": False if level is not None else True
    })
    
    # 過去のデータが膨大になりすぎないよう、直近200件（約8日分）に制限
    history[river_name] = history[river_name][-200:]
    
    os.makedirs(os.path.dirname(WATER_LOG_FILE), exist_ok=True)
    with open(WATER_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def fetch_water_level(url, default_val):
    """
    app.pyと同様に異常値フィルターを実装した水位取得関数
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
                for m_str in matches:
                    val = float(m_str)
                    if abs(val - default_val) <= 1.0:
                        extracted_val = val
                        break
                if extracted_val is None:
                    extracted_val = float(matches[0])
        
        # 異常値（基準値から1.0m以上離れた値）の弾き出し
        if extracted_val is not None:
            if abs(extracted_val - default_val) <= 1.0:
                return extracted_val
            else:
                print(f"異常値検知: {extracted_val}m (基準値 {default_val}m) のため無視します。")
                return None
                
        return None
    except Exception as e:
        print(f"スクレイピングエラー ({url}): {e}")
        return None

def optimize_parameters(params, current_level):
    """
    河川別のパラメータ自動最適化（AI学習ロジック）
    """
    if current_level is None:
        return params

    base_level = params.get("base_level", 1.0)
    diff = current_level - base_level

    current_decay = params.get("decay_rate", 0.9975)
    if diff > 0.5:
        new_decay = max(current_decay * 0.99, current_decay * 0.95)
    else:
        new_decay = min(current_decay * 1.01, current_decay * 1.05)
    
    params["decay_rate"] = round(float(new_decay), 5)
    params["last_valid_level"] = current_level
    params["last_success_time"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    
    return params

def main():
    params_data = load_json(PARAMS_FILE)
    if not params_data:
        print("パラメータファイルが見つかりません。")
        return

    # グラフ表示用に日本時間で「YYYY-MM-DD HH:00」の形式を作成
    now_hour_str = datetime.now(JST).strftime("%Y-%m-%d %H:00")

    for river_name, params in params_data.items():
        url = params.get("url")
        base_level = params.get("base_level", 1.0)
        print(f"処理中: {river_name} (URL: {url})")
        
        # 水位データ取得（基準値を渡して異常値を弾く）
        current_level = fetch_water_level(url, base_level)
        
        if current_level is not None:
            save_water_history(river_name, now_hour_str, current_level)
            print(f"-> 水位 {current_level}m を履歴に保存しました。")
        else:
            print("-> 有効な水位データが取得できませんでした。")
        
        # パラメータの自動最適化（学習）を実行
        updated_params = optimize_parameters(params, current_level)
        params_data[river_name] = updated_params

    # 更新されたパラメータと学習結果を保存
    save_json(params_data, PARAMS_FILE)
    print("すべての河川のパラメータ最適化とデータ更新が完了しました。")

if __name__ == "__main__":
    main()
