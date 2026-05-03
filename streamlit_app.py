import streamlit as st
import pandas as pd
import google.generativeai as genai

# Page Configuration
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.markdown("<h1 style='text-align: center; color: #d4af37;'>🏆 Suryavanshi Auto-Tax</h1>", unsafe_allow_html=True)

# API Connection
if "gemini" in st.secrets:
    api_key = st.secrets["gemini"]["api_key"]
    try:
        genai.configure(api_key=api_key)
        # Gemini 1.5 Flash use kar rahe hain jo fast aur compatible hai
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.sidebar.success("✅ AI Engine Connected!")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Error: {e}")
else:
    st.error("❌ API Key missing in Secrets!")

# Sidebar: Tally Sync
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
        st.success("Tally Masters Loaded!")

# Main Section
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    if st.button("🚀 Start AI Extraction"):
        with st.spinner("AI reading PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # AI Prompt
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_bytes},
                    "Extract Date, Description, and Amount from this statement and show in a Markdown table."
                ])
                
                if response.text:
                    st.success("🎯 Data Extracted!")
                    st.markdown(response.text)
                
            except Exception as e:
                st.error(f"⚠️ Technical Error: {e}")
