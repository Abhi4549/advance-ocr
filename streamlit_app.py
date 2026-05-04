import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf
import hashlib

# --- SECURE LOGIN LOGIC ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Fake Database (Asli business ke liye hum isse Firebase se connect karenge)
USER_DB = {
    "advocate_ajay": {"pwd": make_hashes("admin123"), "plan": "Platinum", "used": 120, "limit": 5000},
    "test_user": {"pwd": make_hashes("pass123"), "plan": "Silver", "used": 950, "limit": 1000}
}

# --- PRO UI ---
st.set_page_config(page_title="Suryavanshi SaaS", layout="wide")
st.markdown("<style>.stApp {background-color: #0e1117; color: white;}</style>", unsafe_allow_html=True)

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 Suryavanshi SaaS Login</h1>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            username = st.text_input("Username / Email")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                if username in USER_DB and check_hashes(password, USER_DB[username]["pwd"]):
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = username
                    st.session_state['user_data'] = USER_DB[username]
                    st.rerun()
                else:
                    st.error("Galti hai! Sahi Username ya Password daalein.")
            st.info("Demo: advocate_ajay / admin123")
else:
    # --- DASHBOARD (AFTER LOGIN) ---
    user = st.session_state['user']
    user_data = st.session_state['user_data']
    
    st.sidebar.markdown(f"### 👤 Welcome, {user.upper()}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    # Subscription Stats
    with st.sidebar:
        st.write("---")
        st.markdown(f"**Plan:** {user_data['plan']}")
        usage_pct = (user_data['used'] / user_data['limit'])
        st.progress(usage_pct if usage_pct <= 1.0 else 1.0)
        st.write(f"Consumption: **{user_data['used']} / {user_data['limit']}** Entries")
        
        if user_data['used'] >= user_data['limit']:
            st.error("🚨 Limit Over! Upgrade karein.")

    # Main App Logic
    st.markdown(f"<h2 style='color: #d4af37;'>🏆 {user.upper()}'s ACCOUNTING DASHBOARD</h2>", unsafe_allow_html=True)
    
    tally_file = st.file_uploader("Upload Tally Masters (Required)", type=['xlsx'])
    bank_pdf = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])
    pdf_pwd = st.text_input("PDF Password", type="password")

    if bank_pdf and tally_file:
        if st.button("🚀 PROCESS STATEMENT"):
            if user_data['used'] < user_data['limit']:
                with st.spinner("AI Engine Working..."):
                    try:
                        # Processing (Same logic as before)
                        pdf_bytes = bank_pdf.getvalue()
                        if pdf_pwd:
                            with pikepdf.open(io.BytesIO(pdf_bytes), password=pdf_pwd) as pdf:
                                dec_io = io.BytesIO(); pdf.save(dec_io); pdf_bytes = dec_io.getvalue()
                        
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        model = genai.GenerativeModel('models/gemini-1.5-flash')
                        
                        response = model.generate_content([
                            {"mime_type": "application/pdf", "data": pdf_bytes},
                            "Extract all transactions as JSON: Date, Narration, Amount."
                        ])
                        
                        raw_text = response.text.replace('```json', '').replace('```', '').strip()
                        df = pd.read_json(io.StringIO(raw_text))
                        
                        # Update Usage
                        new_entries = len(df)
                        st.session_state['user_data']['used'] += new_entries
                        
                        st.success(f"Entries Processed: {new_entries}")
                        st.dataframe(df)
                        
                        # Download Button
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Result", csv, f"audit_{user}.csv")
                        
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Aapka quota khatam ho gaya hai. Upgrade button par click karein.")
