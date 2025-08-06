
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("🚖 タクシー給与予測アプリ（入力フォーム版）")

# 入力フォーム
st.markdown("### 📋 日次データ入力フォーム")
with st.form("input_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        date = st.date_input("日付", value=datetime.today())
    with col2:
        revenue = st.number_input("営収（円）", min_value=0, step=1000)
    with col3:
        departure = st.time_input("出庫時刻", value=datetime.strptime("17:00", "%H:%M").time())
    with col4:
        return_ = st.time_input("帰庫時刻", value=datetime.strptime("03:30", "%H:%M").time())

    submitted = st.form_submit_button("➕ 入力して追加")

# データ保持用セッションステート
if "entries" not in st.session_state:
    st.session_state.entries = []

# データ追加
if submitted:
    st.session_state.entries.append({
        "日付": date.strftime("%Y-%m-%d"),
        "営収": revenue,
        "出庫時刻": departure.strftime("%H:%M"),
        "帰庫時刻": return_.strftime("%H:%M")
    })

# データ表示
if st.session_state.entries:
    df = pd.DataFrame(st.session_state.entries)

    # 自動計算
    df["深夜時間(h)"] = 0.0
    df["超過時間(h)"] = 0.0

    for i, row in df.iterrows():
        out_time = datetime.strptime(f"{row['日付']} {row['出庫時刻']}", "%Y-%m-%d %H:%M")
        in_time = datetime.strptime(f"{row['日付']} {row['帰庫時刻']}", "%Y-%m-%d %H:%M")
        if in_time <= out_time:
            in_time += timedelta(days=1)
        total_hours = (in_time - out_time).total_seconds() / 3600

        # 深夜時間計算（22:00〜5:00）
        night_hours = 0.0
        current = out_time
        while current < in_time:
            if current.hour >= 22 or current.hour < 5:
                next_time = min(current + timedelta(minutes=30), in_time)
                duration = (next_time - current).total_seconds() / 3600
                night_hours += duration
            current += timedelta(minutes=30)
        overtime = max(0.0, total_hours - 9)
        df.at[i, "深夜時間(h)"] = round(night_hours, 2)
        df.at[i, "超過時間(h)"] = round(overtime, 2)

    st.markdown("### 📊 入力済みデータ")
    st.dataframe(df, use_container_width=True)
