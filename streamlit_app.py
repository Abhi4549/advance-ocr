import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf
import hashlib

# --- 1. SECURE LOGIN & DATABASE ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database (Aap yahan naye users add kar sakte hain)
USER_DB = {
    "advocate_ajay": {"pwd": make_hashes("admin123"), "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- 2. PERMANENT API FIX ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        if "gemini" in st.secrets:
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            
            # Kal wala error fix: Explicitly using stable model path
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_bytes},
                prompt
            ])
            return response.text
        else:
            st.error("API Key missing in Streamlit Secrets!")
            return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# --- 3. UI CONFIGURATION ---
st.set_page_config(page_title="Suryavanshi Auto-Tax Pro", layout="wide")
st.markdown("""
    <style>
    .stApp {background-color: #0e1117; color: white;}
    .stButton>button {width: 100%; background-color: #d4af37; color: black; font-weight: bold;}
    .sidebar-text {font-size: 14px; color: #d4af37;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. AUTHENTICATION CHECK ---
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
                st.error("Invalid Credentials!")
else:
    # --- 5. DASHBOARD (POST-LOGIN) ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']
    
    st.sidebar.markdown(f"### 👤 Welcome, {user.upper()}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    with st.sidebar:
        st.write("---")
        st.markdown(f"<p class='sidebar-text'>Current Plan: {u_data['plan']}</p>", unsafe_allow_html=True)
        usage_pct = u_data['used'] / u_data['limit']
        st.progress(usage_pct if usage_pct <= 1.0 else 1.0)
        st.write(f"Usage: {u_data['used']} / {u_data['limit']} Entries")

    st.markdown(f"<h2 style='color: #d4af37; text-align: center;'>🏆 {user.upper()}'S AUDIT ENGINE</h2>", unsafe_allow_html=True)

    # File Inputs
    tally_file = st.file_uploader("1. Sync Tally Masters (Excel)", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Upload Bank PDF (Protected or Regular)", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Leave blank if NO password)", type="password")

    ledgers = []
    if tally_file:
        try:
            ld_df = pd.read_excel(tally_file)
            ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
            st.success(f"✅ {len(ledgers)} Ledgers Synced!")
        except: st.error("Excel format galat hai.")

    if bank_pdf:
        if st.button("🚀 EXECUTE AI AUDIT"):
            if u_data['used'] < u_data['limit']:
                with st.spinner("Analyzing Statement..."):
                    try:
                        raw_bytes = bank_pdf.getvalue()
                        final_bytes = raw_bytes

                        # Password Handling Fix
                        if pdf_pwd:
                            try:
                                with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                                    dec_io = io.BytesIO()
                                    pdf.save(dec_io)
                                    final_bytes = dec_io.getvalue()
                                    st.info("🔓 File Decrypted Successfully.")
                            except:
                                st.error("❌ Wrong Password!")
                                st.stop()

                        # AI Analysis
                        audit_prompt = """
                        Extract all bank transactions. Return ONLY a valid JSON list.
                        Structure: [{"Date": "DD-MM-YYYY", "Narration": "...", "Amount": 123.45}]
                        If messy, use OCR. Ignore extra text.
                        """
                        
                        raw_ai_text = get_gemini_response(final_bytes, audit_prompt)
                        
                        if raw_ai_text:
                            # Cleanup JSON
                            clean_json = raw_ai_text.replace('```json', '').replace('```', '').strip()
                            df = pd.read_json(io.StringIO(clean_json))

                            # Match Tally Ledgers
                            def find_ledger(n):
                                n = str(n).upper()
                                for l in ledgers:
                                    if l.upper() in n: return l
                                return "SUSPENSE ACCOUNT"
                            
                            df['Tally_Ledger'] = df['Narration'].apply(find_ledger)
                            df['Is_Duplicate'] = df.duplicated(subset=['Date', 'Amount'], keep=False)

                            # Update Usage
                            st.session_state['user_data']['used'] += len(df)
                            
                            st.success(f"Audit Complete! {len(df)} Entries Processed.")
                            st.dataframe(df, use_container_width=True)
                            
                            # CSV Download
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 DOWNLOAD FOR TALLY", csv, f"audit_{user}.csv")

                    except Exception as e:
                        st.error(f"Processing Error: {e}")
            else:
                st.warning("Limit over! Please upgrade your plan.")
