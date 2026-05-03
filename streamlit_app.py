import streamlit as st
import pandas as pd
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- API CONNECTION ---
if "gemini" in st.secrets:
    try:
        # Direct configure Bina version mismatch ke
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.success("✅ Engine Connected!")
    except Exception as e:
        st.error(f"Config Error: {e}")
else:
    st.error("API Key missing in Secrets!")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
        st.success("Tally Masters Loaded!")

# --- MAIN ---
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    if st.button("Start AI Extraction"):
        with st.spinner("AI is analyzing PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Gemini 1.5 format
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_bytes},
                    "Extract Date, Description, and Amount from this statement and give a table."
                ])
                
                if response.text:
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"Technical Error: {e}")
