import streamlit as st
import pandas as pd
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- Model Selection Logic ---
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    # Hum 'models/' prefix ke saath specify karenge
    # Agar flash-latest na chale toh ye gemini-1.5-flash par switch karega
    model_name = "models/gemini-1.5-flash-latest"
    model = genai.GenerativeModel(model_name=model_name)
else:
    st.error("API Key missing in Secrets!")

# --- Sidebar: Ledger Sync ---
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
        st.success("Tally Masters Loaded!")

# --- Main Section ---
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    if st.button("Start AI Extraction"):
        with st.spinner("AI is analyzing the PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Naya Content Format
                response = model.generate_content([
                    "Extract Date, Narration, and Amount from this statement. Output as a Markdown table.",
                    {"mime_type": "application/pdf", "data": pdf_bytes}
                ])
                
                if response.text:
                    st.success("Data mil gaya!")
                    st.markdown(response.text)
                
            except Exception as e:
                # Agar 404 phir bhi aaye, toh hum model list print karwayenge debugging ke liye
                st.error(f"Technical Error: {e}")
                if "404" in str(e):
                    st.info("System refresh ho raha hai. Ek baar 'Reboot App' karke dekhein.")
