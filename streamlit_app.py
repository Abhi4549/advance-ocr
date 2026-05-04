import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- LOGIN DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- UI CONFIG ---
st.set_page_config(page_title="Suryavanshi Audit", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.title("🔐 Suryavanshi Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type='password')
    if st.button("Login"):
        if u in USER_DB and p == USER_DB[u]["pwd"]:
            st.session_state['logged_in'] = True
            st.session_state['user'] = u
            st.session_state['user_data'] = USER_DB[u]
            st.rerun()
        else:
            st.error("Invalid credentials")
else:
    # --- DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']

    st.sidebar.title(f"Welcome {user.upper()}")
    st.sidebar.write(f"Usage: {u_data['used']} / {u_data['limit']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.header("📊 Bank Statement Auditor")
    
    bank_pdf = st.file_uploader("Upload Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("PDF Password (Optional)", type="password")

    if bank_pdf and st.button("🚀 Process"):
        with st.spinner("Processing..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO(); pdf.save(out); raw_bytes = out.getvalue()
                
                # API Call
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content([{"mime_type": "application/pdf", "data": raw_bytes}, "Extract transactions as JSON list."])
                
                st.write(res.text) # Pehle check karte hain response aa raha hai ya nahi
                    
            except Exception as e:
                st.error(f"App Error: {e}")
