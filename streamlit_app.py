import streamlit as st
import pandas as pd
import google.generativeai as genai

# Page Setup
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.markdown("<h1 style='text-align: center; color: #d4af37;'>🏆 Suryavanshi Auto-Tax</h1>", unsafe_allow_html=True)

# --- SAHI MODEL KA SELECTION ---
if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        
        # Hum 'gemini-1.5-flash' ki jagah 'gemini-1.5-pro' ya older stable version try karenge
        # Ye version sabse zyada compatible hota hai
        model = genai.GenerativeModel('gemini-1.5-pro') 
        
    except Exception as e:
        st.error(f"Configuration Error: {e}")
else:
    st.error("API Key missing in Secrets!")

# --- STEP 1: SIDEBAR ---
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
        st.success("Tally Masters Loaded!")

# --- STEP 2: PDF SECTION ---
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    if st.button("Start AI Extraction"):
        with st.spinner("AI is reading PDF... (Wait 15-20s)"):
            try:
                pdf_bytes = bank_pdf.getvalue()
                
                # Naya Content Format jo error nahi dega
                content = [
                    {"mime_type": "application/pdf", "data": pdf_bytes},
                    "Extract all transactions from this PDF. Provide a table with Date, Narration, and Amount columns only."
                ]
                
                response = model.generate_content(content)
                
                if response.text:
                    st.success("Data mil gaya!")
                    st.markdown(response.text)
                else:
                    st.warning("AI response empty. Try a different PDF.")
                    
            except Exception as e:
                # Agar 'gemini-1.5-pro' bhi 404 de, toh hum last option 'gemini-pro' use karenge
                st.info("Trying alternative engine...")
                try:
                    model_alt = genai.GenerativeModel('gemini-pro')
                    # Note: gemini-pro direct PDF nahi leta, isliye hum text try karenge
                    st.error("Ye PDF version abhi support nahi ho raha. Ek baar Google AI Studio mein model list check karein.")
                except:
                    st.error(f"Final Technical Error: {e}")
