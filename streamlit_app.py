import streamlit as st
import pandas as pd
import google.generativeai as genai
import pikepdf
import io

# 1. Dashboard ka look set karna (Gold & Dark Theme)
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.markdown("<h1 style='text-align: center; color: #d4af37;'>🏆 Suryavanshi Auto-Tax</h1>", unsafe_allow_html=True)

# 2. AI Key connect karna (Secrets se uthayega)
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Pehle Streamlit Settings mein Gemini API Key daalein!")

# 3. Sidebar: Tally Ledger Sync
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Tally Ledger Export (Excel) yahan daalein", type=['xlsx'])
    
    ledger_options = []
    if tally_file:
        df_ledgers = pd.read_excel(tally_file)
        ledger_options = df_ledgers.iloc[:, 0].tolist() # Pehla column ledger names maan kar
        st.success(f"{len(ledger_options)} Ledgers mil gaye!")
        st.session_state['ledgers'] = ledger_options

# 4. Main Screen: PDF Uploader
st.write("---")
bank_pdf = st.file_uploader("Step 2: Bank Statement PDF upload karein", type=['pdf'])

if bank_pdf:
    st.info("AI PDF ko scan kar raha hai... Agle step mein hum data extract karenge.")
    
    # User ko interface dikhane ke liye sample table
    if 'ledgers' in st.session_state:
        st.subheader("Data Preview & Mapping")
        test_data = pd.DataFrame({
            "Date": ["2026-05-01"],
            "Narration": ["Sample Entry - Zomato"],
            "Amount": [500.00],
            "Tally Ledger": [""]
        })
        
        # Interactive Table
        st.data_editor(
            test_data,
            column_config={
                "Tally Ledger": st.column_config.SelectboxColumn(
                    "Assign Tally Head",
                    options=st.session_state['ledgers'],
                    width="large",
                )
            },
            hide_index=True,
        )
