import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- Nayi Key ke saath Connection ---
if "gemini" in st.secrets:
    try:
        # Nayi library version v1 use karti hai jo stable hai
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # 'models/gemini-1.5-flash' hi likhna hai
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.success("✅ Nayi API Key Connect Ho Gayi!")
    except Exception as e:
        st.error(f"Connection Error: {e}")
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
        with st.spinner("AI is reading PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Simple extraction prompt
                response = model.generate_content([
                    "Extract Date, Narration, and Amount from this statement. Give table.",
                    {"mime_type": "application/pdf", "data": pdf_bytes}
                ])
                
                if response.text:
                    st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Abhi bhi error hai: {e}")
                st.info("Tip: GitHub mein requirements.txt mein 'google-generativeai>=0.5.4' zaroor likhein.")
