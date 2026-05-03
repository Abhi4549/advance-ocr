import streamlit as st
import pandas as pd
import google.generativeai as genai

# UI Branding
st.set_page_config(page_title="Suryavanshi Auto-Tax Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #d4af37;'>🏆 SURYAVANSHI AUTO-TAX PRO</h1>", unsafe_allow_html=True)

# API Setup
if "gemini" in st.secrets:
    api_key = st.secrets["gemini"]["api_key"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("API Key missing! Check Streamlit Secrets.")

# Sidebar: Tally Sync
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
        st.success("Tally Masters Loaded!")

# Main Section
st.subheader("Step 2: Bank Statement Extraction")
bank_pdf = st.file_uploader("Upload Bank PDF", type=['pdf'])

if bank_pdf:
    if st.button("🚀 EXECUTE EXTRACTION"):
        with st.spinner("AI is reading... Please wait."):
            try:
                pdf_data = bank_pdf.getvalue()
                
                # Pro Prompt
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_data},
                    "Extract Date, Narration, and Amount from this statement. Provide only a Markdown table."
                ])
                
                if response.text:
                    st.success("Extraction Done!")
                    st.markdown(response.text)
                else:
                    st.warning("No text found.")
            except Exception as e:
                st.error(f"Technical Error: {e}")
