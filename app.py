import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ตั้งค่าหน้าตาแอปให้รองรับ Mobile
st.set_page_config(page_title="สต๊อกเครื่องเย็นช่างหน้างาน", page_icon="❄️", layout="centered")

# CSS สำหรับปรับแต่งให้ปุ่มใหญ่ ตัวอักษรชัด
st.markdown("""
    <style>
    html, body, [data-testid="stSidebarUserContent"] { font-size: 1.1rem; }
    .stButton>button { width: 100%; padding: 15px; font-size: 1.3rem !important; font-weight: bold; border-radius: 10px; margin-bottom: 10px; }
    .warning-box { background-color: #ffcccc; color: #cc0000; padding: 15px; border-radius: 10px; font-weight: bold; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)


# --- [วางทับตรงนี้] เริ่มต้นส่วนการเชื่อมต่อฐานข้อมูล Google Sheets ---

# 1. ประกาศตัวเชื่อมต่อเชื่อมไปยัง Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. ฟังก์ชันดึงข้อมูลล่าสุด (ดึงจากแท็บ parts และ history)
def load_data():
    # ดึงข้อมูลจากแผ่นงานชื่อ parts และ history
    parts_df = conn.read(worksheet="parts", ttl="0")       # ttl="0" เพื่อบังคับดึงข้อมูลสดใหม่ตลอดเวลา
    history_df = conn.read(worksheet="history", ttl="0")
    return parts_df, history_df

# 3. เรียกใช้งานฟังก์ชันดึงข้อมูลมาเก็บไว้ในตัวแปรสำหรับใช้งานในแอป
df_parts, df_history = load_data()

# ปรับประเภทข้อมูลตัวเลขจำนวนให้ถูกต้อง ป้องกันความผิดพลาดตอนคำนวณ
df_parts['quantity'] = df_parts['quantity'].astype(int)
df_parts['min_stock'] = df_parts['min_stock'].astype(int)


# 4. ฟังก์ชันสำหรับอัปเดตสต๊อกกลับไปยัง Google Sheets เมื่อช่างกดปุ่ม
def update_stock_gsheets(part_idx, change_amount, action_type, tech_name, current_parts_df, current_history_df):
    # คำนวณจำนวนสต๊อกใหม่ในแถวที่เลือก
    current_parts_df.at[part_idx, 'quantity'] += change_amount
    
    # บันทึกประวัติกิจกรรมของช่างเพิ่มเข้าไป 1 บรรทัด
    new_log = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "part_name": current_parts_df.at[part_idx, 'name'],
        "action": action_type,
        "amount": abs(change_amount),
        "technician": tech_name if tech_name else "ไม่ระบุชื่อ"
    }])
    
    # นำประวัติใหม่ไปต่อเชื่อมด้านบนสุดของประวัติเดิม
    updated_history_df = pd.concat([new_log, current_history_df], ignore_index=True)
    
    # สั่งเขียนข้อมูลทับกลับไปยัง Google Sheets ทั้ง 2 แท็บทันที
    conn.update(worksheet="parts", data=current_parts_df)
    conn.update(worksheet="history", data=updated_history_df)

# --- จบส่วนระบบจัดการฐานข้อมูลหลังบ้าน ---


# --- ส่วนแสดงผล UI ---
st.title("❄️ ระบบสต๊อกเครื่องเย็น (ผ่าน Google Sheets)")

# ฟีเจอร์: แจ้งเตือนของใกล้หมด
low_stock_parts = df_parts[df_parts['quantity'] <= df_parts['min_stock']]
if not low_stock_parts.empty:
    st.markdown("### ⚠️ ของใกล้หมด! รีบแจ้งส่วนกลาง")
    for _, row in low_stock_parts.iterrows():
        st.markdown(f"<div class='warning-box'>🚨 {row['name']} เหลือแค่ {row['quantity']} ชิ้น (ขั้นต่ำ {row['min_stock']})</div>", unsafe_allow_html=True)

# เมนูหลักด้านบน
menu = st.radio("เลือกเมนูที่ต้องการ", ["📦 เบิก/รับอะไหล่", "🔍 เช็คสต๊อกทั้งหมด", "📜 ประวัติการเบิกของ"], horizontal=True)
st.markdown("---")

# MENU 1: เบิก/รับอะไหล่
if menu == "📦 เบิก/รับอะไหล่":
    st.subheader("บันทึกการ เบิกออก (-) หรือ รับเข้า (+)")
    tech_name = st.text_input("👤 ชื่อช่างผู้ทำรายการ:", placeholder="พิมพ์ชื่อของคุณที่นี่")
    search_query = st.selectbox("🛠️ เลือกอะไหล่ที่ต้องการ:", df_parts['name'].tolist())
    
    part_idx = df_parts[df_parts['name'] == search_query].index[0]
    current_qty = df_parts.at[part_idx, 'quantity']
    
    st.metric(label="จำนวนคงเหลือตอนนี้", value=f"{current_qty} ชิ้น")
    amount = st.number_input("🔢 จำนวน (ชิ้น):", min_value=1, value=1, step=1)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔴 เบิกออก (-)", type="secondary"):
            if current_qty >= amount:
                with st.spinner("กำลังบันทึกลง Google Sheets..."):
                    update_stock_gsheets(part_idx, -amount, "เบิกออก (-)", tech_name, df_parts, df_history)
                st.success("บันทึกการเบิกสำเร็จ!")
                st.rerun()
            else:
                st.error("❌ ของในสต๊อกไม่พอเบิก!")
                
    with col2:
        if st.button("🟢 รับเข้า (+)", type="primary"):
            with st.spinner("กำลังบันทึกลง Google Sheets..."):
                update_stock_gsheets(part_idx, amount, "รับเข้า (+)", tech_name, df_parts, df_history)
            st.success("บันทึกการรับเข้าสำเร็จ!")
            st.rerun()

# MENU 2: เช็คสต๊อกทั้งหมด
elif menu == "🔍 เช็คสต๊อกทั้งหมด":
    st.subheader("📦 รายการอะไหล่ทั้งหมดในคลัง")
    search = st.text_input("🔍 พิมพ์ค้นหาชื่ออะไหล่:", placeholder="เช่น น้ำยาแอร์, คอม...")
    
    filtered_df = df_parts
    if search:
        filtered_df = df_parts[df_parts['name'].str.contains(search, case=False)]
        
    for _, row in filtered_df.iterrows():
        status_color = "🔴 ของหมด" if row['quantity'] == 0 else ("🟡 ใกล้หมด" if row['quantity'] <= row['min_stock'] else "🟢 ปกติ")
        st.markdown(f"""
        <div style='padding: 15px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 10px;'>
            <h4 style='margin:0;'>{row['name']}</h4>
            <p style='margin:5px 0; font-size:1.2rem;'><b>คงเหลือ: {row['quantity']} ชิ้น</b> ({status_color})</p>
            <small style='color:gray;'>หมวดหมู่: {row['category']} | รหัส: {row['id']}</small>
        </div>
        """, unsafe_allow_html=True)

# MENU 3: ประวัติการเบิกของ
elif menu == "📜 ประวัติการเบิกของ":
    st.subheader("📋 ประวัติการทำรายการล่าสุดจากฐานข้อมูล")
    if df_history.empty or df_history.dropna().empty:
        st.info("ยังไม่มีประวัติการเบิกหรือรับของในระบบ")
    else:
        st.dataframe(df_history, hide_index=True, use_container_width=True)