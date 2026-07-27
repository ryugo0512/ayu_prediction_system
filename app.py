import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="河川状況＆パラメータ最適化ビューア", layout="wide")

DATA_DIR = "data"
PARAMS_FILE = os.path.join(DATA_DIR, "river_params.json")
WATER_LEVELS_FILE = os.path.join(DATA_DIR, "water_levels.json")

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

st.title("🌊 河川状況・AIパラメータ自動最適化ダッシュボード")
st.markdown("GitHub Actionsによって自動収集された最新データと、河川別の自動学習パラメータを確認できます。")

params_data = load_json(PARAMS_FILE)
water_levels_data = load_json(WATER_LEVELS_FILE)

# パラメータデータと水位データの両方から河川リストを取得
all_rivers = sorted(list(set(list(params_data.keys()) + list(water_levels_data.keys()))))

if not all_rivers:
    st.warning("⚠️ データが見つかりません。バッチ処理の実行をお待ちください。")
else:
    selected_river = st.selectbox("対象河川の選択", all_rivers)

    if selected_river:
        river_info = params_data.get(selected_river, {})

        # 最新ステータス表示
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

        # 過去の水位データ推移（グラフ・テーブル）の表示
        st.subheader("📈 過去の水位データ推移")
        history = water_levels_data.get(selected_river, [])

        if history:
            df = pd.DataFrame(history)

            # エラーなしデータのみ抽出
            if "fetch_error" in df.columns:
                df = df[df["fetch_error"] == False]

            if not df.empty and "timestamp" in df.columns and "water_level" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp")

                # 折れ線グラフ表示
                chart_data = df.set_index("timestamp")[["water_level"]]
                st.line_chart(chart_data)

                # 詳細データのテーブル表示
                with st.expander("水位履歴データ（詳細一覧）"):
                    display_df = df[["timestamp", "water_level"]].rename(columns={
                        "timestamp": "日時",
                        "water_level": "水位 (m)"
                    })
                    st.dataframe(display_df, use_container_width=True)
            else:
                st.info("有効な水位履歴データがありません。")
        else:
            st.info("この河川の水位履歴データが存在しないか空です。")

        st.markdown("---")
        st.subheader("⚙️ 河川別学習パラメータ詳細")
        if river_info:
            st.json(river_info)
        else:
            st.info("パラメータデータが存在しません。")
