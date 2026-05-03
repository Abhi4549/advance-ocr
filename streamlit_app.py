import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. Page Config & Branding
st.set_page_config(page_title="Suryavanshi Auto-Tax", layout="wide")
st.markdown("<h1 style='text-align: center; color: #d4af37;'>🏆 Suryavanshi Auto-Tax</h1>", unsafe_allow_html=True)

# 2. AI Connection Check
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Secrets mein API Key nahi mili! Pehle Streamlit settings check karein.")

# 3. Sidebar: Ledger Mapping (Wapas add kiya gaya)
with st.sidebar:
    st.header("Step 1: Sync Tally")
    tally_file = st.file_uploader("Tally Ledger Export (Excel) upload karein", type=['xlsx'])
    
    if tally_file:
        try:
            df_ledgers = pd.read_excel(tally_file)
            # Pehle column ko ledger name maan rahe hain
            st.session_state['ledgers'] = df_ledgers.iloc[:, 0].dropna().unique().tolist()
            st.success(f"{len(st.session_state['ledgers'])} Ledgers loaded!")
        except Exception as e:
            st.error(f"Excel error: {e}")

# 4. Main Section: PDF Upload
st.write("---")
bank_pdf = st.file_uploader("Step 2: Upload Bank Statement (PDF)", type=['pdf'])

if bank_pdf:
    pdf_data = bank_pdf.getvalue() # File content read karna
    
    if st.button("Start AI Extraction"):
        with st.spinner("AI reading PDF... Isme 15-20 seconds lag sakte hain."):
            try:
                # AI ko instructions
                prompt = "Extract transaction data from this bank statement. Return it in a clear table format with columns: Date, Narration, Amount."
                
                # AI Call with safety checks
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_data},
                    prompt
                ])
                
                if response.text:
                    st.success("Data Extracted!")
                    st.markdown(response.text)
                    
                    # Sidebar mein ledgers hain toh mapping option dikhayenge
                    if 'ledgers' in st.session_state:
                        st.info("Aap upar ke data ko niche dropdown se map kar sakte hain.")
                else:
                    st.warning("AI ne response nahi diya. Please try again.")
                    
            except Exception as e:
                st.error(f"Technical Error: {e}")
                st.info("Tip: Kya aapne Streamlit Secrets mein 'api_key' sahi se likha hai?")
