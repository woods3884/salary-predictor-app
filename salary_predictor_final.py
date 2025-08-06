import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

st.title("🚖 タクシー給与予測アプリ")

# --- 入力フォーム ---
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
    submitted = st.form_submit_button("➕ 追加")

# --- セッションステートにデータ保持 ---
if "entries" not in st.session_state:
    st.session_state.entries = []

if submitted:
    st.session_state.entries.append({
        "日付": date.strftime("%Y-%m-%d"),
        "営収": revenue,
        "出庫時刻": departure.strftime("%H:%M"),
        "帰庫時刻": return_.strftime("%H:%M")
    })

# --- データ表示と削除処理 ---
if st.session_state.entries:
    df = pd.DataFrame(st.session_state.entries)

    st.markdown("### 🗑 入力済みデータ（削除可）")
    for idx, row in df.iterrows():
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(row["日付"])
        cols[1].write(f"¥{row['営収']:,}")
        cols[2].write(row["出庫時刻"])
        cols[3].write(row["帰庫時刻"])
        # 削除ボタンを押したら該当行をセッションステートから削除し、再レンダリングを停止
        if cols[4].button("削除", key=f"del_{idx}"):
            st.session_state.entries.pop(idx)
            st.stop()

    # 再度 DataFrame を生成
    df = pd.DataFrame(st.session_state.entries)

    # --- 深夜・超過時間の自動計算 ---
    df["深夜時間(h)"] = 0.0
    df["超過時間(h)"] = 0.0
    for i, row in df.iterrows():
        out_time = datetime.strptime(f"{row['日付']} {row['出庫時刻']}", "%Y-%m-%d %H:%M")
        in_time  = datetime.strptime(f"{row['日付']} {row['帰庫時刻']}", "%Y-%m-%d %H:%M")
        if in_time <= out_time:
            in_time += timedelta(days=1)
        total_hours = (in_time - out_time).total_seconds() / 3600

        # 深夜時間（22:00～翌5:00）計算
        night_h = 0.0
        current = out_time
        while current < in_time:
            if current.hour >= 22 or current.hour < 5:
                nxt = min(current + timedelta(minutes=30), in_time)
                night_h += (nxt - current).total_seconds() / 3600
            current += timedelta(minutes=30)
        over_h = max(0.0, total_hours - 9)

        df.at[i, "深夜時間(h)"] = round(night_h, 2)
        df.at[i, "超過時間(h)"] = round(over_h, 2)

    # 表形式で表示
    st.markdown("### 📊 入力済みデータ")
    st.dataframe(df, use_container_width=True)

    # --- 給与計算と PDF 出力は「営収」列がある場合のみ ---
    if "営収" in df.columns and not df.empty:
        total_sales  = df["営収"].sum()
        night_hours  = df["深夜時間(h)"].sum()
        over_hours   = df["超過時間(h)"].sum()

        rate_table = {
            900000: 508712, 850000: 471015, 800000: 438359, 750000: 404286,
            700000: 369718, 650000: 329678, 600000: 288907, 550000: 252054,
            500000: 211921, 450000: 170255, 400000: 122505
        }
        base_pay = 0
        for thr, amt in sorted(rate_table.items(), reverse=True):
            if total_sales >= thr:
                base_pay = amt
                break

        night_pay = int(night_hours * 600)
        over_pay  = int(over_hours * 250)
        total_pay = base_pay + night_pay + over_pay
        deduction = int(total_pay * 0.115)
        take_home = total_pay - deduction

        # 給与結果表示
        st.markdown("### 💰 給与予測結果")
        st.write(f"総営収：¥{total_sales:,}")
        st.write(f"歩合給（基準額）：¥{base_pay:,}")
        st.write(f"深夜手当：¥{night_pay:,}（{night_hours:.1f}h）")
        st.write(f"超過手当：¥{over_pay:,}（{over_hours:.1f}h）")
        st.write(f"支給合計：¥{total_pay:,}")
        st.write(f"控除（11.5%）：¥{deduction:,}")
        st.success(f"👉 手取り見込み：¥{take_home:,}")

        # --- PDF 出力機能 ---
        def generate_pdf(df):
            buf = BytesIO()
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
            c = canvas.Canvas(buf, pagesize=A4)
            width, height = A4
            c.setFont('HeiseiKakuGo-W5', 12)
            # ヘッダー
            c.drawString(50, height-50, "🚖 タクシー給与レポート")
            # 対象期間
            start = df["日付"].min()
            end   = df["日付"].max()
            c.drawString(50, height-80, f"対象期間：{start} ～ {end}")
            # 金額詳細
            ypos = height-120
            c.drawString(50, ypos, f"総営収：¥{total_sales:,}"); ypos -= 20
            c.drawString(50, ypos, f"歩合給：¥{base_pay:,}"); ypos -= 20
            c.d