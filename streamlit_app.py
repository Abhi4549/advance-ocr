import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- USER DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- PAGE SETUP ---
st.set_page_config(page_title="Suryavanshi Audit Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN LOGIC ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 SURYAVANSHI LOGIN</h1>", unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type='password')
    if st.button("Access Dashboard"):
        if u in USER_DB and p == USER_DB[u]["pwd"]:
            st.session_state['logged_in'] = True
            st.session_state['user'] = u
            st.session_state['user_data'] = USER_DB[u]
            st.rerun()
        else:
            st.error("Invalid Credentials!")
else:
    # --- DASHBOARD AREA ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']

    st.sidebar.title(f"👤 {user.upper()}")
    st.sidebar.write(f"Usage: {u_data['used']} / {u_data['limit']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("🏆 Bank Statement Auditor")
    
    bank_pdf = st.file_uploader("Upload Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("PDF Password (Optional)", type="password")

    if bank_pdf and st.button("🚀 Process Now"):
        with st.spinner("AI is working..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                
                # Decrypt if password exists
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO()
                        pdf.save(out)
                        raw_bytes = out.getvalue()

                # API Setup - Using Stable v1 path
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # AI Call
                res = model.generate_content([
                    {"mime_type": "application/pdf", "data": raw_bytes},
                    "Extract all transactions into a JSON list with keys: Date, Narration, Amount."
                ])
                
                if res.text:
                    clean_json = res.text.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean_json))
                    st.session_state['user_data']['used'] += len(df)
                    st.success(f"Success! Found {len(df)} entries.")
                    st.dataframe(df, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Technical Error: {e}")
