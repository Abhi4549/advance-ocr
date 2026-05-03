import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- API Connection ---
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    
    # Model select karne ka sabse safe tareeka
    # Hum 'gemini-1.5-flash' ko version specify karke call karenge
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
else:
    st.error("API Key missing in Secrets!")

# --- Sidebar ---
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
        with st.spinner("AI reading PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Naya content passing style jo newest version ko support karta hai
                response = model.generate_content([
                    "Extract Date, Description, and Amount from this statement and present as a table.",
                    {"mime_type": "application/pdf", "data": pdf_bytes}
                ])
                
                if response.text:
                    st.success("Data mil gaya!")
                    st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Technical Error: {e}")
                st.info("Tip: Ek baar Google AI Studio mein jaakar check karein ki kya wahan Gemini 1.5 Flash 'Active' hai?")
