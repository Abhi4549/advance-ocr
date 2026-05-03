import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# --- API KEY CHECK ---
if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.success("✅ AI Connection Established!")
    except Exception as e:
        st.error(f"❌ API Configuration Error: {e}")
else:
    st.error("❌ API Key Missing! Go to Streamlit Settings > Secrets.")

# --- SIDEBAR FOR TALLY LEDGERS ---
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].tolist()
        st.success(f"{len(st.session_state['ledgers'])} Ledgers Synced!")

# --- MAIN PDF UPLOADER ---
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    if st.button("Start AI Extraction"):
        with st.spinner("AI is reading..."):
            try:
                # File content reading
                pdf_bytes = bank_pdf.getvalue()
                
                # Simple prompt
                response = model.generate_content([
                    "List all transactions from this bank statement as a table with Date, Narration, and Amount.",
                    {"mime_type": "application/pdf", "data": pdf_bytes}
                ])
                
                if response.text:
                    st.markdown(response.text)
                else:
                    st.warning("AI didn't find any data.")
            except Exception as e:
                st.error(f"⚠️ Technical Error Details: {str(e)}")
