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
st.set_page_config(page_title="Suryavanshi Audit SaaS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 SURYAVANSHI LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        u = st.text_input("Username")
        p = st.text_input("Password", type='password')
        if st.button("Enter Dashboard"):
            if u in USER_DB and p == USER_DB[u]["pwd"]:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.session_state['user_data'] = USER_DB[u]
                st.rerun()
            else:
                st.error("Invalid Credentials")
else:
    # --- DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']

    with st.sidebar:
        st.header(f"👤 {user.upper()}")
        st.write(f"Plan: {u_data['plan']}")
        st.write(f"Usage: {u_data['used']} / {u_data['limit']}")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title("📊 Bank Statement Auditor")
    
    bank_pdf = st.file_uploader("Upload Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("PDF Password (if any)", type="password")

    if bank_pdf and st.button("🚀 Process Statement"):
        with st.spinner("AI Engine Working..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                
                # Password Logic
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO(); pdf.save(out); raw_bytes = out.getvalue()
                
                # Stable API Call
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Simple prompt for testing
                res = model.generate_content([
                    {"mime_type": "application/pdf", "data": raw_bytes},
                    "Extract all transactions into a JSON list with Date, Narration, and Amount."
                ])
                
                if res.text:
                    clean_json = res.text.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean_json))
                    st.session_state['user_data']['used'] += len(df)
                    st.success(f"Extracted {len(df)} rows!")
                    st.dataframe(df)
                    st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), "audit.csv")
                    
            except Exception as e:
                st.error(f"App Error: {e}")
