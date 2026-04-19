import streamlit as st
import pandas as pd
import sqlite3
from google import genai
from google.genai import types
import json

# ดึง API Key
gemini_api_key = st.secrets["gemini_api_key"]
gmn_client = genai.Client(api_key=gemini_api_key)

# รายละเอียดฐานข้อมูล
db_name = 'test_database.db'
data_table = 'transactions'
data_dict_text = """
- trx_date: วันที่ทําธุรกรรม
- trx_no: หมายเลขธุรกรรม
- member_code: รหัสสมาชิกของลูกค้า
- branch_code: รหัสสาขา
- branch_region: ภูมิภาคที่สาขาต้องอยู่
- branch_province: จังหวัดที่สาขาต้องอยู่
- product_code: รหัสสินค้า
- product_category: หมวดหมู่หลักของสินค้า
- product_group: กลุ่มของสินค้า
- product_type: ประเภทของสินค้า
- order_qty: จํานวนชิ้น/หน่วย ที่ลูกค้าสั่งซื้อ
- unit_price: ราคาขายของสินค้าต่อ 1 หน่วย
- cost: ต้นทุนของสินค้าต่อ 1 หน่วย
- item_discount: ส่วนลดเฉพาะรายการสินค้านั้นๆ
- customer_discount: ส่วนลดจากสิทธิของลูกค้า
- net_amount: ยอดขายสุทธิของรายการนั้น
- cost_amount: ต้นทุนรวมของรายการนั้น
"""
# HELPER FUNCTIONS
def query_to_dataframe(sql_query, database_name):
  """รัน SQL และคืนค่าเป็น DataFrame"""
  try:
    connection = sqlite3.connect(database_name)
    result_df = pd.read_sql_query(sql_query, connection)
    connection.close()
    return result_df
  except Exception as e:
    return f"Database Error: {e}"

def generate_gemini_answer(prompt, is_json=False):
  """เรียก Gemini API"""
  try:
    config = types.GenerateContentConfig(
      response_mime_type="application/json" if is_json else "text/plain" )
    response = gmn_client.models.generate_content(
      model='gemini-2.5-flash-lite',
      contents=prompt,
      config=config)
    return response.text
  except Exception as e:
    return f"AI Error: {e}"

# PROMPT TEMPLATES
script_prompt = """
### Goal
### Context
### Input
### Process
### Output
(ห้ามมีคําอธิบายประกอบ หรือ Markdown นอกเหนือจาก JSON)
"""

answer_prompt = """
### Goal
### Context
### Input
### Process
### Output
"""

# CORE LOGIC
def generate_summary_answer(user_question):
  # 1. ดึง Schema จาก session_state มาใช้ใน Prompt
  script_prompt_input = script_prompt.format(
    question=user_question,
    table_name=data_table,
    data_dict=data_dict_text
)
sql_json_text = call_gemini(script_prompt_input, is_json=True)
try:
  sql_script = json.loads(sql_json_text)['script']
except:
  return "ขออภัย ไม่สามารถสร้างคําสั่ง SQL ได้"\

# 2. Query ข้อมูล
df_result = query_to_dataframe(sql_script, db_name)
if isinstance(df_result, str):
  return df_result
# 3. สรุปคําตอบ
answer_prompt_input = answer_prompt.format(
  question=user_question,
  raw_data=df_result.to_string()
)
return generate_gemini_answer(answer_prompt_input, is_json=False)

# USER INTERFACE
# ตรวจสอบและสร้าง Chat History ใน Session State
if "messages" not in st.session_state:
  st.session_state.messages = []
  
st.title('Gemini Chat with Database')

# แสดงประวัติการสนทนา
for message in st.session_state.messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])

# รับ Input
if prompt := st.chat_input("พิมพ์คําถามที่นี่..."):
  # เก็บและแสดงข้อความ User
  st.session_state.messages.append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)
    
# ประมวลผลและแสดงข้อความ Assistant
with st.chat_message("assistant"):
  with st.spinner('กําลังหาคําตอบ...'):
  response = generate_summary_answer(prompt)
    st.markdown(response)

# เก็บคําตอบลง Session
st.session_state.messages.append({"role": "assistant", "content": response})
