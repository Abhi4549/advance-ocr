import streamlit as st
import pandas as pd
import google.generativeai as genai
import base64

# --- PAGE SETUP ---
st.set_page_config(page_title="Suryavanshi Auto-Tax Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color: #d4af37;'>🏆 SURYAVANSHI AUTO-TAX PRO</h1>", unsafe_allow_html=True)

# --- AI ENGINE ---
if "gemini" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        
        # List available models to debug
        try:
            available_model_list = genai.list_models()
            model_names = [m.name.split('/')[-1] for m in available_model_list if 'generateContent' in m.supported_generation_methods]
            st.sidebar.info(f"📋 Available models: {', '.join(model_names[:3])}")
        except:
            pass
        
        # Try most compatible older models
        available_models = ['gemini-pro-vision', 'gemini-pro', 'gemini-1.5-flash']
        model = None
        selected_model = None
        
        for model_name in available_models:
            try:
                model = genai.GenerativeModel(model_name)
                selected_model = model_name
                st.sidebar.success(f"✅ AI Engine Ready ({model_name})")
                break
            except Exception as e:
                continue
        
        if not model:
            st.sidebar.error("❌ No compatible Gemini model found. Please check available models.")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Error: {e}")
else:
    st.error("❌ API Key missing! Check Streamlit Secrets.")

# --- SIDEBAR: TALLY SYNC ---
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Upload Tally Masters (Excel)", type=['xlsx'])
    if tally_file:
        try:
            df = pd.read_excel(tally_file)
            st.session_state['ledgers'] = df.iloc[:, 0].dropna().unique().tolist()
            st.success(f"✅ {len(st.session_state['ledgers'])} Ledgers Loaded")
        except Exception as e:
            st.error(f"Excel Error: {e}")

# --- MAIN: PDF EXTRACTION ---
st.subheader("Step 2: Bank Statement Extraction")
bank_pdf = st.file_uploader("Upload Bank PDF", type=['pdf'])

if bank_pdf:
    if st.button("🚀 EXECUTE AI EXTRACTION"):
        with st.spinner("AI is analyzing the statement..."):
            try:
                pdf_bytes = bank_pdf.getvalue()
                pdf_base64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
                
                # Instruction for the AI
                prompt = "Extract all transactions into a Markdown table with columns: Date, Narration, Amount. Only provide the table."
                
                # Use base64 encoded PDF
                response = model.generate_content([
                    {
                        "mime_type": "application/pdf",
                        "data": pdf_base64,
                    },
                    prompt
                ])
                
                if response.text:
                    st.success("🎯 Data Extracted Successfully!")
                    st.markdown(response.text)
                else:
                    st.warning("AI couldn't find readable data.")
            except Exception as e:
                st.error(f"⚠️ Technical Error: {e}")
                st.info(f"📌 Using model: {selected_model}")
