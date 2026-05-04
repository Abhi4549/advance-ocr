import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf
import hashlib

# --- SECURE LOGIN & HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database (Add your users here)
USER_DB = {
    "advocate_ajay": {"pwd": make_hashes("admin123"), "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- PAGE CONFIG ---
st.set_page_config(page_title="Suryavanshi SaaS Pro", layout="wide")
st.markdown("""
    <style>
    .stApp {background-color: #0e1117; color: white;}
    .stButton>button {background-color: #d4af37; color: black; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

# --- AUTHENTICATION FLOW ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 SURYAVANSHI SaaS LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        if st.button("Access Dashboard"):
            if username in USER_DB and check_hashes(password, USER_DB[username]["pwd"]):
                st.session_state['logged_in'] = True
                st.session_state['user'] = username
                st.session_state['user_data'] = USER_DB[username]
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
else:
    # --- DASHBOARD LOADED ---
    user = st.session_state['user']
    user_data = st.session_state['user_data']
    
    st.sidebar.markdown(f"### 👤 Welcome, {user.upper()}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    with st.sidebar:
        st.write("---")
        st.markdown(f"**Current Plan:** {user_data['plan']}")
        usage_pct = (user_data['used'] / user_data['limit'])
        st.progress(usage_pct if usage_pct <= 1.0 else 1.0)
        st.write(f"Usage: **{user_data['used']} / {user_data['limit']}** Entries")

    st.markdown(f"<h2 style='color: #d4af37;'>🏆 {user.upper()}'S UNIVERSAL AUDIT ENGINE</h2>", unsafe_allow_html=True)

    # File Uploaders
    tally_file = st.file_uploader("1. Sync Tally Ledgers (Excel)", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Upload Bank Statement (Any Bank PDF)", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Leave blank if NO password)", type="password")

    ledgers = []
    if tally_file:
        ld_df = pd.read_excel(tally_file)
        ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()

    if bank_pdf:
        if st.button("🚀 START AI EXTRACTION"):
            if user_data['used'] < user_data['limit']:
                with st.spinner("AI is reading the file... Please wait."):
                    try:
                        raw_pdf_bytes = bank_pdf.getvalue()
                        final_pdf_bytes = raw_pdf_bytes

                        # --- SMART PASSWORD HANDLING ---
                        if pdf_pwd:
                            try:
                                with pikepdf.open(io.BytesIO(raw_pdf_bytes), password=pdf_pwd) as pdf:
                                    dec_io = io.BytesIO()
                                    pdf.save(dec_io)
                                    final_pdf_bytes = dec_io.getvalue()
                                    st.info("🔓 Password applied. File decrypted.")
                            except pikepdf.PasswordError:
                                st.error("❌ Galat Password! Check karein.")
                                st.stop()
                        
                        # --- AI ENGINE ---
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        model = genai.GenerativeModel('models/gemini-1.5-flash')
                        
                        # Universal OCR Prompt
                        prompt = """
                        You are a Professional Bank Auditor. Extract all transactions from this statement.
                        - Identify Date, Narration/Description, and Amount.
                        - Even if the PDF is scanned or messy, use OCR to find data.
                        - Return ONLY a valid JSON list of objects.
                        - Format: [{"Date": "DD-MM-YYYY", "Narration": "...", "Amount": 123.45}]
                        """
                        
                        response = model.generate_content([
                            {"mime_type": "application/pdf", "data": final_pdf_bytes},
                            prompt
                        ])
                        
                        # Data Cleaning
                        res_text = response.text.replace('```json', '').replace('```', '').strip()
                        df = pd.read_json(io.StringIO(res_text))

                        # Smart Ledger Match
                        def match_it(n):
                            n = str(n).upper()
                            for l in ledgers:
                                if l.upper() in n: return l
                            return "SUSPENSE ACCOUNT"
                        
                        df['Suggested_Ledger'] = df['Narration'].apply(match_it)
                        df['Is_Duplicate'] = df.duplicated(subset=['Date', 'Amount'], keep=False)

                        # Update Session Usage
                        st.session_state['user_data']['used'] += len(df)
                        
                        st.success(f"Successfully processed {len(df)} entries.")
                        
                        # Display & Download
                        st.dataframe(df, use_container_width=True)
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 DOWNLOAD AUDITED CSV", csv, "audit_result.csv")

                    except Exception as e:
                        st.error(f"Something went wrong: {e}")
            else:
                st.warning("Quota over! Please recharge.")
