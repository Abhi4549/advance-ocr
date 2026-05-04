import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf
import hashlib

# --- 1. SECURE AUTHENTICATION ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Static Database
USER_DB = {
    "advocate_ajay": {"pwd": make_hashes("admin123"), "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- 2. THE ULTIMATE API FIX (NO MORE 404) ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        if "gemini" in st.secrets:
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            
            # FIXED: Yahan hum explicitly 'gemini-1.5-flash' use kar rahe hain 
            # bina 'models/' prefix ke, jo naye SDK mein 404 fix karta hai.
            model = genai.GenerativeModel(model_name='gemini-1.5-flash')
            
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_bytes},
                prompt
            ])
            return response.text
        else:
            st.error("Secrets mein API Key nahi mili!")
            return None
    except Exception as e:
        # Fallback for older versions if needed
        st.error(f"API Error Logic Triggered: {e}")
        return None

# --- 3. DASHBOARD UI ---
st.set_page_config(page_title="Suryavanshi SaaS Pro", layout="wide")
st.markdown("""
    <style>
    .stApp {background-color: #0e1117; color: white;}
    .stButton>button {width: 100%; background-color: #d4af37; color: black; font-weight: bold; border-radius: 8px;}
    .sidebar-stats {padding: 10px; border: 1px solid #d4af37; border-radius: 5px; background-color: #1e2130;}
    </style>
    """, unsafe_allow_html=True)

# --- 4. SESSION MANAGEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 SURYAVANSHI SaaS LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u_name = st.text_input("Username")
        u_pass = st.text_input("Password", type='password')
        if st.button("Access Engine"):
            if u_name in USER_DB and check_hashes(u_pass, USER_DB[u_name]["pwd"]):
                st.session_state['logged_in'] = True
                st.session_state['user'] = u_name
                st.session_state['user_data'] = USER_DB[u_name]
                st.rerun()
            else:
                st.error("Invalid Credentials!")
else:
    # --- 5. LOGGED IN DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']
    
    with st.sidebar:
        st.markdown(f"### 👤 {user.upper()}")
        st.markdown("<div class='sidebar-stats'>", unsafe_allow_html=True)
        st.write(f"**Plan:** {u_data['plan']}")
        usage = u_data['used'] / u_data['limit']
        st.progress(usage if usage <= 1.0 else 1.0)
        st.write(f"Usage: {u_data['used']} / {u_data['limit']}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("---")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown(f"<h2 style='color: #d4af37;'>🏆 {user.upper()}'S UNIVERSAL AUDIT ENGINE</h2>", unsafe_allow_html=True)

    # Inputs
    tally_file = st.file_uploader("1. Sync Tally Ledger List (Excel)", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Upload Bank Statement (PDF)", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Leave blank if NO password)", type="password")

    ledgers = []
    if tally_file:
        try:
            ld_df = pd.read_excel(tally_file)
            ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
            st.success(f"✅ {len(ledgers)} Tally Ledgers Ready")
        except: st.error("Excel format issue.")

    if bank_pdf:
        if st.button("🚀 EXECUTE AI EXTRACTION"):
            if u_data['used'] < u_data['limit']:
                with st.spinner("AI Engine is auditing the statement..."):
                    try:
                        raw_data = bank_pdf.getvalue()
                        processed_bytes = raw_data

                        # Password Decryption
                        if pdf_pwd:
                            try:
                                with pikepdf.open(io.BytesIO(raw_data), password=pdf_pwd) as pdf:
                                    out = io.BytesIO()
                                    pdf.save(out)
                                    processed_bytes = out.getvalue()
                                    st.info("🔓 PDF Unlocked.")
                            except:
                                st.error("❌ Wrong PDF Password!")
                                st.stop()

                        # AI Processing
                        prompt = """
                        Return ONLY a JSON list of all transactions.
                        Format: [{"Date": "DD-MM-YYYY", "Narration": "...", "Amount": 123.45}]
                        Include every single transaction found.
                        """
                        
                        ai_response = get_gemini_response(processed_bytes, prompt)
                        
                        if ai_response:
                            # JSON Cleaning
                            clean_data = ai_response.replace('```json', '').replace('```', '').strip()
                            df = pd.read_json(io.StringIO(clean_data))

                            # Ledger Matching
                            def find_match(narration):
                                narration = str(narration).upper()
                                for l in ledgers:
                                    if l.upper() in narration: return l
                                return "SUSPENSE ACCOUNT"
                            
                            df['Suggested_Ledger'] = df['Narration'].apply(find_match)
                            df['Is_Duplicate'] = df.duplicated(subset=['Date', 'Amount'], keep=False)

                            # Usage Counter Update
                            st.session_state['user_data']['used'] += len(df)
                            
                            st.success(f"Audit Complete: {len(df)} entries found.")
                            st.dataframe(df, use_container_width=True)
                            
                            # Download
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 DOWNLOAD AUDITED CSV", csv, f"audit_{user}.csv")

                    except Exception as e:
                        st.error(f"Technical Glitch: {e}")
            else:
                st.warning("Quota exhausted! Please renew.")
