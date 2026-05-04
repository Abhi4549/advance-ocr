import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- 1. SIMPLE LOGIN (No Hashing for direct access) ---
# Username: advocate_ajay | Password: admin123
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- 2. THE PERMANENT API FIX (v1 STABLE) ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        if "gemini" in st.secrets:
            # Force API Configuration
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            
            # CRITICAL FIX: Direct model name string without 'models/' prefix
            # This bypasses the v1beta 404 error
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_bytes},
                prompt
            ])
            return response.text
        else:
            st.error("Secrets mein API Key nahi mili!")
            return None
    except Exception as e:
        # Error reporting for debugging
        st.error(f"API Error Details: {e}")
        return None

# --- 3. UI & DASHBOARD CONFIG ---
st.set_page_config(page_title="Suryavanshi Audit SaaS", layout="wide")
st.markdown("""
    <style>
    .stApp {background-color: #0e1117; color: white;}
    .stButton>button {background-color: #d4af37; color: black; font-weight: bold; width: 100%;}
    .stProgress > div > div > div > div { background-color: #d4af37; }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 4. LOGIN SCREEN ---
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
                st.error("Invalid Username or Password!")
else:
    # --- 5. LOGGED IN AREA ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']
    
    with st.sidebar:
        st.header(f"👤 {user.upper()}")
        st.write(f"Plan: **{u_data['plan']}**")
        # Usage Progress Bar
        usage_pct = u_data['used'] / u_data['limit']
        st.progress(usage_pct if usage_pct <= 1.0 else 1.0)
        st.write(f"Quota: {u_data['used']} / {u_data['limit']}")
        st.write("---")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown(f"<h2 style='color: #d4af37; text-align: center;'>🏆 {user.upper()}'S AUDIT ENGINE</h2>", unsafe_allow_html=True)

    # Main Inputs
    tally_file = st.file_uploader("1. Upload Tally Masters (Excel)", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Upload Bank Statement (PDF)", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Optional)", type="password")

    ledgers = []
    if tally_file:
        try:
            ld_df = pd.read_excel(tally_file)
            ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
            st.success(f"✅ {len(ledgers)} Ledgers Synced")
        except: st.error("Excel format issue.")

    if bank_pdf and st.button("🚀 EXECUTE AI AUDIT"):
        if u_data['used'] < u_data['limit']:
            with st.spinner("AI Engine is auditing..."):
                try:
                    raw_bytes = bank_pdf.getvalue()
                    final_bytes = raw_bytes

                    # Password Handling
                    if pdf_pwd:
                        try:
                            with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                                out = io.BytesIO()
                                pdf.save(out)
                                final_bytes = out.getvalue()
                                st.info("🔓 PDF Unlocked.")
                        except:
                            st.error("❌ Wrong PDF Password!")
                            st.stop()

                    # Audit Prompt
                    prompt = "Extract all transactions. Return ONLY a valid JSON list. Format: [{'Date': 'DD-MM-YYYY', 'Narration': '...', 'Amount': 123.45}]"
                    
                    res = get_gemini_response(final_bytes, prompt)
                    
                    if res:
                        # Cleanup AI extra text
                        clean = res.replace('```json', '').replace('```', '').strip()
                        df = pd.read_json(io.StringIO(clean))
                        
                        # Ledger Matching Logic
                        def match_ledger(narration):
                            narration = str(narration).upper()
                            for l in ledgers:
                                if l.upper() in narration: return l
                            return "SUSPENSE ACCOUNT"
                        
                        df['Suggested_Ledger'] = df['Narration'].apply(match_ledger)
                        
                        # Update Usage Counter
                        st.session_state['user_data']['used'] += len(df)
                        
                        st.success(f"Audit Complete! {len(df)} Entries Found.")
                        st.dataframe(df, use_container_width=True)
                        
                        # Download Link
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 DOWNLOAD CSV", csv_data, f"audit_{user}.csv")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Quota Exhausted! Please recharge.")
