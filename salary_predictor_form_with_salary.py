
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


    # 給与計算ロジック追加
    total_sales = df["営収"].sum()
    night_hours = df["深夜時間(h)"].sum()
    over_hours = df["超過時間(h)"].sum()

    rate_table = {
        900000: 508712, 850000: 471015, 800000: 438359, 750000: 404286,
        700000: 369718, 650000: 329678, 600000: 288907, 550000: 252054,
        500000: 211921, 450000: 170255, 400000: 122505
    }
    base_pay = 0
    for threshold, amount in sorted(rate_table.items(), reverse=True):
        if total_sales >= threshold:
            base_pay = amount
            break

    night_pay = int(night_hours * 600)
    over_pay = int(over_hours * 250)
    total_pay = base_pay + night_pay + over_pay
    deduction = int(total_pay * 0.115)
    take_home = total_pay - deduction

    st.markdown("### 💰 給与予測結果")
    st.write(f"総営収：¥{int(total_sales):,}")
    st.write(f"歩合給（基準額）：¥{base_pay:,}")
    st.write(f"深夜手当：¥{night_pay:,}（{night_hours:.1f}h）")
    st.write(f"超過手当：¥{over_pay:,}（{over_hours:.1f}h）")
    st.write(f"支給合計：¥{total_pay:,}")
    st.write(f"控除（11.5%）：¥{deduction:,}")
    st.success(f"👉 差引支給額（手取り見込み）：¥{take_home:,}")
