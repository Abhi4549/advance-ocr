import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- FORCE NEW API VERSION ---
if "gemini" in st.secrets:
    try:
        # Naya tareeka: direct configure
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        
        # Hum specifically 'gemini-1.5-flash' ka naya path use karenge
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        st.success("✅ Engine Ready!")
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
        with st.spinner("AI is reading your PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Naya Content Format jo v1 ko support karta hai
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_bytes},
                    "Extract Date, Narration, and Amount from this statement and give a table."
                ])
                
                if response.text:
                    st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Technical Error: {e}")
                # Agar phir bhi 404 aaye toh ye trick try karein
                st.info("Tip: Ek baar Streamlit Settings mein jaakar 'Delete App' karein aur phir se 'Deploy' karein. Isse cache clear ho jayegi.")
