import json
import os
import streamlit as st

st.set_page_config(page_title="河川状況＆パラメータ最適化ビューア", layout="wide")

DATA_DIR = "data"
PARAMS_FILE = os.path.join(DATA_DIR, "river_params.json")

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

st.title("🌊 河川状況・AIパラメータ自動最適化ダッシュボード")
st.markdown("GitHub Actionsによって自動収集された最新データと、河川別の自動学習パラメータを確認できます。")

params_data = load_json(PARAMS_FILE)

if not params_data:
    st.warning("⚠️ パラメータデータ（river_params.json）が見つかりません。バッチ処理の実行をお待ちください。")
else:
    # 河川ごとのタブまたはセクションで表示
    river_names = list(params_data.keys())
    selected_river = st.selectbox("対象河川の選択", river_names)
    
    if selected_river:
        river_info = params_data[selected_river]
        
        # エラーフラグや最終取得成功時刻のチェック
        last_success = river_info.get("last_success_time", "不明")
        last_level = river_info.get("last_valid_level", "取得中...")
        
        st.info(f"📌 **{selected_river}** の最新ステータス (最終更新: {last_success})")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="直近の観測水位", value=f"{last_level} m")
        with col2:
            st.metric(label="現在の減衰率 (Decay)", value=river_info.get("decay_rate", "N/A"))
        with col3:
            st.metric(label="ハミ垢成長係数", value=river_info.get("hamiaka_growth_rate", "N/A"))
        
        st.markdown("---")
        st.subheader("⚙️ 河川別学習パラメータ詳細")
        st.json(river_info)