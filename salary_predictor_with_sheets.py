import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🚖 タクシー給与予測アプリ（Google Sheets連携 + PDF出力）")

# --- Google Sheets認証設定 ---
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('streamlit-access-468203-6c601e68135d.json', scope)
gc = gspread.authorize(creds)

# --- スプレッドシート読み込み ---
sheet_id = st.text_input("🔗 スプレッドシートIDを入力してください", "ここに貼り付け")
df = pd.DataFrame()

if sheet_id and sheet_id != "ここに貼り付け":
    try:
        worksheet = gc.open_by_key(sheet_id).sheet1
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        st.success("✅ Googleスプレッドシートから読み込み成功")
    except Exception as e:
        st.error(f"❌ 読み込みエラー: {e}")

if not df.empty:
    df["深夜時間(h)"] = 0.0
    df["超過時間(h)"] = 0.0

    STANDARD_WORK_HOURS = 9
    NIGHT_START = 22
    NIGHT_END = 5

    for i, row in df.iterrows():
        date_str = row["日付"]
        out_str = row["出庫時刻"]
        in_str = row["帰庫時刻"]

        out_time = datetime.strptime(f"{date_str} {out_str}", "%Y-%m-%d %H:%M")
        in_time = datetime.strptime(f"{date_str} {in_str}", "%Y-%m-%d %H:%M")
        if in_time <= out_time:
            in_time += timedelta(days=1)

        total_hours = (in_time - out_time).total_seconds() / 3600

        night_hours = 0.0
        current = out_time
        while current < in_time:
            if current.hour >= NIGHT_START or current.hour < NIGHT_END:
                next_time = min(current + timedelta(minutes=30), in_time)
                duration = (next_time - current).total_seconds() / 3600
                night_hours += duration
            current += timedelta(minutes=30)

        overtime = max(0.0, total_hours - STANDARD_WORK_HOURS)
        df.at[i, "深夜時間(h)"] = round(night_hours, 2)
        df.at[i, "超過時間(h)"] = round(overtime, 2)

    st.dataframe(df)

    # --- PDF出力機能 ---
    def generate_pdf_report(df, 月名="給与レポート"):
        buffer = BytesIO()
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        c.setFont('HeiseiKakuGo-W5', 12)

        c.drawString(50, height - 50, f"🚖 タクシー給与レポート（{月名}）")
        start = df["日付"].min()
        end = df["日付"].max()
        c.drawString(50, height - 80, f"対象期間：{start} ～ {end}")

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

        ypos = height - 120
        c.drawString(50, ypos, f"総営収：¥{int(total_sales):,}")
        ypos -= 20
        c.drawString(50, ypos, f"基準額（歩合給）：¥{base_pay:,}")
        ypos -= 20
        c.drawString(50, ypos, f"深夜手当（×600円/h）：¥{night_pay:,}（{night_hours:.1f}h）")
        ypos -= 20
        c.drawString(50, ypos, f"超過手当（×250円/h）：¥{over_pay:,}（{over_hours:.1f}h）")
        ypos -= 20
        c.drawString(50, ypos, f"支給合計：¥{total_pay:,}")
        ypos -= 20
        c.drawString(50, ypos, f"控除見込み（11.5%）：¥{deduction:,}")
        ypos -= 20
        c.drawString(50, ypos, f"差引支給（手取り）：¥{take_home:,}")

        c.save()
        buffer.seek(0)
        return buffer

    pdf_buffer = generate_pdf_report(df)
    st.download_button("📥 PDFをダウンロード", data=pdf_buffer, file_name="給与レポート.pdf", mime="application/pdf")
