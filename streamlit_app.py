import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- CONNECTION ---
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    # Hum model ka pura path likhenge taaki 404 na aaye
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
else:
    st.error("Secrets mein API Key nahi mili!")

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
        with st.spinner("AI is reading PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Naya content passing style
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_bytes},
                    "Extract Date, Description, and Amount from this statement and give a table."
                ])
                
                if response.text:
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")
