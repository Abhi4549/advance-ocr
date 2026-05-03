import streamlit as st
import pandas as pd
import google.generativeai as genai

# Page Setup
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.title("🏆 Suryavanshi Auto-Tax")

# API Check
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Secrets mein API Key nahi mili!")

bank_pdf = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    # PDF ko read karne ka naya tareeka
    pdf_data = bank_pdf.getvalue()
    
    if st.button("Start AI Extraction"):
        with st.spinner("AI is reading... (Please wait)"):
            try:
                # AI ko bahut simple instruction dena
                prompt = "Please extract the transaction table from this PDF. I need Date, Narration, and Amount. Just give me the data in a clear list or table."
                
                # AI Call
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_data},
                    prompt
                ])
                
                if response:
                    st.success("Data mil gaya!")
                    st.write(response.text)
                else:
                    st.error("AI ne kuch read nahi kiya. Kya PDF scan copy hai ya digital?")
            
            except Exception as e:
                st.error(f"Technical Error: {e}")
                st.info("Tips: 1. Check if PDF is password protected. 2. Try with a smaller PDF (1-2 pages).")
