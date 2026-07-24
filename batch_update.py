import json
import os
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ファイルパスの定義
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARAMS_FILE = os.path.join(BASE_DIR, 'data', 'river_params.json')
WATER_LOG_FILE = os.path.join(BASE_DIR, 'data', 'water_levels.json')

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_water_level(url):
    """スクレイピングで水位を取得する関数。サイトの構造に合わせて修正が必要です。"""
    try:
        # サイトへの負荷軽減とブロック回避のためのヘッダー設定
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # TODO: 実際のHTML構造に合わせて水位を抽出するロジックを記述してください
        # 例: level_text = soup.find('div', class_='water-level').text
        # ここではテスト用のダミー数値を返します。
        dummy_level = 105.5
        return float(dummy_level)
        
    except Exception as e:
        print(f"水位取得エラー: {e}")
        return None

def main():
    print(f"[{datetime.now()}] バッチ処理を開始します。")
    river_params = load_json(PARAMS_FILE)
    water_logs = load_json(WATER_LOG_FILE)
    current_time = datetime.now().isoformat()

    for river_name, params in river_params.items():
        print(f"--- {river_name} の処理 ---")
        url = params.get('url')
        if not url:
            continue

        # 1. 水位データの取得
        current_level = fetch_water_level(url)
        error_flag = False

        if current_level is not None:
            # 取得成功時のパラメータ更新
            params['last_valid_level'] = current_level
            params['last_success_time'] = current_time
        else:
            # 取得失敗時（フェイルセーフ）
            current_level = params.get('last_valid_level', params.get('base_level'))
            error_flag = True
            print(f"警告: データ取得に失敗したため、前回値（{current_level}）を使用します。")

        # 2. ログへの記録
        if river_name not in water_logs:
            water_logs[river_name] = []
        
        log_entry = {
            "timestamp": current_time,
            "water_level": current_level,
            "fetch_error": error_flag
        }
        water_logs[river_name].append(log_entry)
        
        # ログが増えすぎないように直近720件（1時間ごとなら30日分）に制限
        water_logs[river_name] = water_logs[river_name][-720:]

        # 3. AI学習（係数の自動最適化）処理の呼び出し
        # ※気象データの取得と学習ロジックは次のステップで組み込みます
        
    # データの保存
    save_json(PARAMS_FILE, river_params)
    save_json(WATER_LOG_FILE, water_logs)
    print("バッチ処理が完了し、データが保存されました。")

if __name__ == "__main__":
    main()