import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    # 'gemini-1.5-flash' ki jagah 'gemini-1.5-flash-latest' try karein
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
else:
    st.error("API Key missing in Secrets!")

# Sidebar for Ledger Sync
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    if tally_file:
        df = pd.read_excel(tally_file)
        st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
        st.success("Tally Masters Loaded!")

# Main PDF Section
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    if st.button("Start AI Extraction"):
        with st.spinner("AI reading PDF..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                # Simple prompt for high compatibility
                response = model.generate_content([
                    "Provide a table of all transactions with columns: Date, Description, Amount.",
                    {"mime_type": "application/pdf", "data": pdf_bytes}
                ])
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Tip: Try a smaller PDF or check your API Key status at Google AI Studio.")
