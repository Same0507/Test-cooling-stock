import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="App สต๊อกเครื่องเย็น", page_icon="❄️", layout="centered")

# เชื่อมต่อ Google Sheets (ดึง URL จาก Secrets อัตโนมัติ)
conn = st.connection("gsheets", type=GSheetsConnection)

# ดึงข้อมูลจากแผ่นงาน (Worksheet) ที่แยกกันในไฟล์เดียว
@st.cache_data(ttl=5)
def load_data():
    # อ่านแผ่นงานชื่อ "Inventory"
    inventory_df = conn.read(worksheet="Inventory", usecols=[0, 1, 2, 3, 4])
    # อ่านแผ่นงานชื่อ "History"
    history_df = conn.read(worksheet="History", usecols=[0, 1, 2, 3, 4, 5])
    
    return inventory_df.dropna(how="all"), history_df.dropna(how="all")

try:
    inv_df, hist_df = load_data()
except Exception as e:
    st.error(f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบลิงก์ใน Secrets หรือชื่อแผ่นงาน: {e}")
    st.stop()

# ================= UI เมนูหลัก =================
st.title("❄️ ระบบจัดการสต๊อก")
menu = st.radio("เลือกเมนูการทำงาน:", ["📦 เช็คสต๊อก & ค้นหา", "🔄 เบิก / รับเข้า", "💰 คำนวณค่าซ่อม", "📜 ประวัติรายการ"], horizontal=True)

st.markdown("---")

# ================= 1. หน้าเช็คสต๊อก & ค้นหา =================
if menu == "📦 เช็คสต๊อก & ค้นหา":
    st.subheader("🔍 ค้นหาอะไหล่")
    search_query = st.text_input("พิมพ์ชื่ออะไหล่ที่ต้องการค้นหา:")
    
    low_stock = inv_df[inv_df['quantity'] <= inv_df['min_stock']]
    if not low_stock.empty:
        st.warning(f"⚠️ มีอะไหล่ใกล้หมดสต๊อก {len(low_stock)} รายการ!")
        for index, row in low_stock.iterrows():
            st.error(f"📉 {row['part_name']} (เหลือ {row['quantity']} ชิ้น)")
            
    st.markdown("### รายการอะไหล่ทั้งหมด")
    display_df = inv_df[inv_df['part_name'].str.contains(search_query, na=False, case=False)] if search_query else inv_df
    st.dataframe(display_df[['part_name', 'quantity', 'price_per_unit']], use_container_width=True, hide_index=True)

# ================= 2. หน้าเบิก / รับเข้า =================
elif menu == "🔄 เบิก / รับเข้า":
    st.subheader("บันทึก เบิก-รับ อะไหล่")
    
    tech_name = st.text_input("ชื่อช่าง:")
    action = st.selectbox("ทำรายการ:", ["เบิกของ (นำไปใช้)", "รับเข้า (ซื้อมาเพิ่ม)"])
    part_selected = st.selectbox("เลือกอะไหล่:", inv_df['part_name'].tolist())
    qty = st.number_input("จำนวน:", min_value=1, step=1)
    job_ref = st.text_input("เลขที่งานซ่อม (ถ้ามี):")
    
    if st.button("💾 บันทึกรายการ", type="primary", use_container_width=True):
        if not tech_name:
            st.error("กรุณาใส่ชื่อช่าง!")
        else:
            part_idx = inv_df.index[inv_df['part_name'] == part_selected].tolist()[0]
            current_qty = inv_df.at[part_idx, 'quantity']
            
            if action == "เบิกของ (นำไปใช้)":
                if current_qty < qty:
                    st.error("❌ ของในสต๊อกไม่พอ!")
                    st.stop()
                inv_df.at[part_idx, 'quantity'] = current_qty - qty
            else:
                inv_df.at[part_idx, 'quantity'] = current_qty + qty
                
            new_hist = pd.DataFrame([{
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tech_name": tech_name,
                "action": action,
                "part_name": part_selected,
                "quantity": qty,
                "job_ref": job_ref
            }])
            hist_df = pd.concat([hist_df, new_hist], ignore_index=True)
            
            # บันทึกข้อมูลกลับไปยังแผ่นงาน (Worksheet) ที่ถูกต้อง
            conn.update(worksheet="Inventory", data=inv_df)
            conn.update(worksheet="History", data=hist_df)
            st.cache_data.clear()
            st.success("✅ บันทึกข้อมูลเรียบร้อย!")

# ================= 3. หน้าคำนวณค่าซ่อม =================
elif menu == "💰 คำนวณค่าซ่อม":
    st.subheader("🧮 คำนวณค่าใช้จ่ายงานซ่อม")
    
    selected_parts = st.multiselect("เลือกอะไหล่ที่ใช้:", inv_df['part_name'].tolist())
    labor_cost = st.number_input("ค่าแรงช่าง (บาท):", min_value=0, step=100)
    
    if selected_parts:
        total_parts_cost = 0
        for part in selected_parts:
            price = inv_df.loc[inv_df['part_name'] == part, 'price_per_unit'].values[0]
            st.write(f"- {part} : {price} บาท")
            total_parts_cost += price
            
        st.markdown("---")
        st.metric("รวมค่าอะไหล่", f"{total_parts_cost:,.2f} บาท")
        st.metric("รวมสุทธิ (ค่าอะไหล่ + ค่าแรง)", f"{total_parts_cost + labor_cost:,.2f} บาท")

# ================= 4. หน้าประวัติรายการ =================
elif menu == "📜 ประวัติรายการ":
    st.subheader("ประวัติการเบิก-รับของ")
    st.dataframe(hist_df, use_container_width=True, hide_index=True)