import streamlit as st
import pandas as pd
from datetime import datetime

import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("ตัวอย่างการดึงข้อมูลจาก Google Sheets")

# 1. สร้าง Connection Object
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. อ่านข้อมูลทั้งหมดออกมาเป็น Pandas DataFrame
# (ระบบจะวิ่งไปอ่านไฟล์ตาม URL ที่เราแปะไว้ใน secrets.toml อัตโนมัติ)
df = conn.read()

# 3. นำข้อมูลมาแสดงบน Streamlit App
st.dataframe(df)

# 1. ตั้งค่าหน้าตาแอปให้รองรับ Mobile และปรับขนาดตัวอักษรให้ใหญ่ขึ้น
st.set_page_config(page_title="สต๊อกเครื่องเย็นช่างหน้างาน", page_icon="❄️", layout="centered")

# CSS สำหรับปรับแต่งให้ปุ่มใหญ่ ตัวอักษรชัด เหมาะกับมือถือ
st.markdown("""
    <style>
    html, body, [data-testid="stSidebarUserContent"] {
        font-size: 1.1rem;
    }
    .stButton>button {
        width: 100%;
        padding: 15px;
        font-size: 1.3rem !important;
        font-weight: bold;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .warning-box {
        background-color: #ffcccc;
        color: #cc0000;
        padding: 15px;
        border-radius: 10px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. จำลองฐานข้อมูลด้วย st.session_state
if 'parts_db' not in st.connection("gsheets", type=GSheetsConnection):
    st.session_state.parts_db = pd.DataFrame([
        {"id": "P001", "name": "น้ำยาแอร์ R32 (ถัง)", "quantity": 8, "min_stock": 3, "category": "น้ำยาแอร์"},
        {"id": "P002", "name": "คอมเพรสเซอร์ 12,000 BTU", "quantity": 2, "min_stock": 3, "category": "คอมเพรสเซอร์"},
        {"id": "P003", "name": "คาปาซิเตอร์รัน 35 uF", "quantity": 15, "min_stock": 5, "category": "อะไหล่ไฟฟ้า"},
        {"id": "P004", "name": "ท่อทองแดง 1/2 หนา", "quantity": 1, "min_stock": 2, "category": "ท่อและข้อต่อ"}
    ])

if 'history_db' not in st.session_state:
    st.session_state.history_db = pd.DataFrame(columns=["timestamp", "part_name", "action", "amount", "technician"])

# --- ฟังก์ชันการทำงานหลัก ---
def update_stock(part_idx, change_amount, action_type, tech_name):
    # อัปเดตจำนวนสินค้า
    st.session_state.parts_db.at[part_idx, 'quantity'] += change_amount
    # บันทึกประวัติ
    new_log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "part_name": st.session_state.parts_db.at[part_idx, 'name'],
        "action": action_type,
        "amount": abs(change_amount),
        "technician": tech_name if tech_name else "ไม่ระบุชื่อ"
    }
    st.session_state.history_db = pd.concat([pd.DataFrame([new_log]), st.session_state.history_db], ignore_index=True)

# --- ส่วนแสดงผล UI ---
st.title("❄️ ระบบสต๊อกเครื่องเย็น (สำหรับช่าง)")

# ฟีเจอร์: แจ้งเตือนของใกล้หมด (แสดงด้านบนสุดให้เห็นชัดๆ)
df_parts = st.session_state.parts_db
low_stock_parts = df_parts[df_parts['quantity'] <= df_parts['min_stock']]

if not low_stock_parts.empty:
    st.markdown("### ⚠️ ของใกล้หมด! รีบแจ้งส่วนกลาง")
    for _, row in low_stock_parts.iterrows():
        st.markdown(f"<div class='warning-box'>🚨 {row['name']} เหลือแค่ {row['quantity']}ชิ้น (ขั้นต่ำ {row['min_stock']})</div>", unsafe_allow_html=True)

# เมนูหลักด้านบน แยกสัดส่วนชัดเจน
menu = st.radio("เลือกเมนูที่ต้องการ", ["📦 เบิก/รับอะไหล่", "🔍 เช็คสต๊อกทั้งหมด", "📜 ประวัติการเบิกของ"], horizontal=True)

st.markdown("---")

# MENU 1: เบิก/รับอะไหล่ (หน้างานหลักของช่าง)
if menu == "📦 เบิก/รับอะไหล่":
    st.subheader("บันทึกการ เบิกออก (-) หรือ รับเข้า (+)")
    
    # กรอกชื่อช่าง
    tech_name = st.text_input("👤 ชื่อช่างผู้ทำรายการ:", placeholder="พิมพ์ชื่อของคุณที่นี่")
    
    # ค้นหา/เลือกอะไหล่ (ใช้ Dropdown ขนาดใหญ่ เลือกง่าย)
    search_query = st.selectbox("🛠️ เลือกอะไหล่ที่ต้องการ:", df_parts['name'].tolist())
    
    # ดึงข้อมูลอะไหล่ที่เลือก
    part_idx = df_parts[df_parts['name'] == search_query].index[0]
    current_qty = df_parts.at[part_idx, 'quantity']
    
    st.metric(label="จำนวนคงเหลือตอนนี้", value=f"{current_qty} ชิ้น")
    
    # เลือกจำนวนที่จะเบิกหรือรับเข้า
    amount = st.number_input("🔢 จำนวน (ชิ้น):", min_value=1, value=1, step=1)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔴 เบิกออก (-)", type="secondary"):
            if current_qty >= amount:
                update_stock(part_idx, -amount, "เบิกออก (-)", tech_name)
                st.success("บันทึกการเบิกสำเร็จ!")
                st.rerun()
            else:
                st.error("❌ ของในสต๊อกไม่พอเบิก!")
                
    with col2:
        if st.button("🟢 รับเข้า (+)", type="primary"):
            update_stock(part_idx, amount, "รับเข้า (+)", tech_name)
            st.success("บันทึกการรับเข้าสำเร็จ!")
            st.rerun()

# MENU 2: เช็คสต๊อกทั้งหมด
elif menu == "🔍 เช็คสต๊อกทั้งหมด":
    st.subheader("📦 รายการอะไหล่ทั้งหมดในคลัง")
    
    # ช่องค้นหาด่วน
    search = st.text_input("🔍 พิมพ์ค้นหาชื่ออะไหล่:", placeholder="เช่น น้ำยาแอร์, คอม...")
    
    filtered_df = df_parts
    if search:
        filtered_df = df_parts[df_parts['name'].str.contains(search, case=False)]
        
    # แสดงผลแบบการ์ดขนาดใหญ่เพื่อให้ช่างดูบนมือถือง่าย (ไม่ใช้ Table เล็กๆ)
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
    st.subheader("📋 ประวัติการทำรายการล่าสุด")
    if st.session_state.history_db.empty:
        st.info("ยังไม่มีประวัติการเบิกหรือรับของในระบบ")
    else:
        # แสดงตารางประวัติ
        st.dataframe(
            st.session_state.history_db, 
            column_config={
                "timestamp": "วัน-เวลา",
                "part_name": "ชื่ออะไหล่",
                "action": "กิจกรรม",
                "amount": "จำนวน",
                "technician": "ช่างผู้ทำรายการ"
            },
            hide_index=True,
            use_container_width=True
        )