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
    
    st.markdown("---")
    # เพิ่มตัวเลือกให้เลือกว่าจะใช้อะไหล่เดิม หรือเพิ่มใหม่
    part_option = st.radio("ประเภทอะไหล่:", ["ค้นหาจากระบบ (มีอยู่แล้ว)", "เพิ่มอะไหล่ใหม่ (รับเข้าครั้งแรก)"], horizontal=True)
    
    # ตัวแปรสำหรับเก็บข้อมูลอะไหล่
    price_per_unit = 0.0
    min_stock = 0
    
    if part_option == "ค้นหาจากระบบ (มีอยู่แล้ว)":
        part_selected = st.selectbox("เลือกอะไหล่:", inv_df['part_name'].tolist())
    else:
        part_selected = st.text_input("ชื่ออะไหล่ใหม่:")
        col1, col2 = st.columns(2)
        with col1:
            price_per_unit = st.number_input("ราคาต่อหน่วย (บาท):", min_value=0.0, step=10.0)
        with col2:
            min_stock = st.number_input("จุดแจ้งเตือนของหมด (Min Stock):", min_value=0, step=1)
            
        if action == "เบิกของ (นำไปใช้)":
            st.warning("⚠️ การเพิ่มชื่ออะไหล่ใหม่ ควรเป็นการทำรายการ 'รับเข้า (ซื้อมาเพิ่ม)'")

    st.markdown("---")
    qty = st.number_input("จำนวน:", min_value=1, step=1)
    job_ref = st.text_input("เลขที่งานซ่อม (ถ้ามี):")
    
    if st.button("💾 บันทึกรายการ", type="primary", use_container_width=True):
        if not tech_name:
            st.error("กรุณาใส่ชื่อช่าง!")
        elif not part_selected:
            st.error("กรุณาระบุชื่ออะไหล่!")
        else:
            # กรณี: เพิ่มอะไหล่ใหม่
            if part_option == "เพิ่มอะไหล่ใหม่ (รับเข้าครั้งแรก)":
                if part_selected in inv_df['part_name'].values:
                    st.error("❌ มีอะไหล่ชื่อนี้ในระบบแล้ว กรุณากลับไปเลือก 'ค้นหาจากระบบ'")
                    st.stop()
                if action == "เบิกของ (นำไปใช้)":
                    st.error("❌ ไม่สามารถเบิกอะไหล่ที่ยังไม่มีในสต๊อกได้ กรุณาเปลี่ยนเป็น 'รับเข้า'")
                    st.stop()
                
                # สร้าง DataFrame สำหรับอะไหล่ใหม่
                new_part_data = {
                    "part_name": part_selected,
                    "quantity": qty,
                    "price_per_unit": price_per_unit,
                    "min_stock": min_stock
                }
                new_inv = pd.DataFrame([new_part_data])
                inv_df = pd.concat([inv_df, new_inv], ignore_index=True)
                
            # กรณี: อะไหล่เดิมที่มีในระบบ
            else:
                part_idx = inv_df.index[inv_df['part_name'] == part_selected].tolist()[0]
                current_qty = inv_df.at[part_idx, 'quantity']
                
                if action == "เบิกของ (นำไปใช้)":
                    if current_qty < qty:
                        st.error(f"❌ ของในสต๊อกไม่พอ! (มีอยู่ {current_qty} ชิ้น)")
                        st.stop()
                    inv_df.at[part_idx, 'quantity'] = current_qty - qty
                else:
                    inv_df.at[part_idx, 'quantity'] = current_qty + qty
                    
            # บันทึกประวัติลง History
            new_hist = pd.DataFrame([{
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tech_name": tech_name,
                "action": action,
                "part_name": part_selected,
                "quantity": qty,
                "job_ref": job_ref
            }])
            hist_df = pd.concat([hist_df, new_hist], ignore_index=True)
            
            # บันทึกข้อมูลกลับไปยัง Google Sheets
            conn.update(worksheet="Inventory", data=inv_df)
            conn.update(worksheet="History", data=hist_df)
            st.cache_data.clear()
            st.success(f"✅ บันทึกรายการ {action} สำหรับ '{part_selected}' จำนวน {qty} ชิ้น เรียบร้อย!")

# ================= 3. หน้าคำนวณค่าซ่อม =================
elif menu == "💰 คำนวณค่าซ่อม":
    st.subheader("🧮 คำนวณค่าใช้จ่ายงานซ่อม")
    
    # 1. เลือกอะไหล่ที่ใช้ (Multiselect)
    selected_parts = st.multiselect("เลือกอะไหล่ที่ใช้:", inv_df['part_name'].tolist())
    
    # 2. กรอกค่าแรง
    labor_cost = st.number_input("ค่าแรงช่าง (บาท):", min_value=0, step=100)
    
    total_parts_cost = 0.0
    
    if selected_parts:
        st.markdown("### 📝 รายละเอียดและจำนวน")
        
        # สร้าง loop เพื่อสร้างช่องกรอกจำนวนสำหรับแต่ละอะไหล่ที่เลือก
        for part in selected_parts:
            # ดึงราคาต่อหน่วยจาก DataFrame
            price = inv_df.loc[inv_df['part_name'] == part, 'price_per_unit'].values[0]
            
            # แบ่งคอลัมน์เพื่อให้ UI ดูสวยงาม (ชื่ออะไหล่ | ช่องกรอกจำนวน | ราคารวม)
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                st.write(f"**{part}**")
                st.caption(f"ราคาหน่วยละ {price:,.2f} บาท")
            
            with col2:
                # ใช้ key โดยการรวมชื่ออะไหล่ เพื่อไม่ให้ ID ของ widget ซ้ำกัน
                qty = st.number_input(f"จำนวนที่ใช้", min_value=1, step=1, key=f"qty_{part}")
                
            with col3:
                item_total = price * qty
                st.write(f"**{item_total:,.2f} บาท**")
            
            total_parts_cost += item_total
            
        st.markdown("---")
        
        # แสดงผลสรุป
        c1, c2 = st.columns(2)
        with c1:
            st.metric("รวมค่าอะไหล่ทั้งสิ้น", f"{total_parts_cost:,.2f} บาท")
        with c2:
            st.metric("รวมสุทธิ (อะไหล่ + ค่าแรง)", f"{total_parts_cost + labor_cost:,.2f} บาท")
            
        # ปุ่มสำหรับช่วยสรุปข้อความ (เผื่อก๊อปปี้ไปส่งงาน)
        if st.button("📋 สรุปรายการสำหรับส่งงาน"):
            summary_text = f"🛠️ สรุปค่าซ่อม\n"
            summary_text += f"----------------\n"
            for part in selected_parts:
                p = inv_df.loc[inv_df['part_name'] == part, 'price_per_unit'].values[0]
                summary_text += f"- {part} x{qty} ชิ้น\n"
            summary_text += f"----------------\n"
            summary_text += f"รวมค่าอะไหล่: {total_parts_cost:,.2f} บาท\n"
            summary_text += f"ค่าแรงช่าง: {labor_cost:,.2f} บาท\n"
            summary_text += f"ยอดรวมสุทธิ: {total_parts_cost + labor_cost:,.2f} บาท"
            st.code(summary_text)

# ================= 4. หน้าประวัติรายการ =================
elif menu == "📜 ประวัติรายการ":
    st.subheader("ประวัติการเบิก-รับของ")
    st.dataframe(hist_df, use_container_width=True, hide_index=True)