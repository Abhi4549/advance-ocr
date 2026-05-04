import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- CHAMBER LOGIN DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 10000},
}

# --- UI CONFIGURATION ---
st.set_page_config(page_title="BizOps Auto-Tax Engine", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- SECURE LOGIN PORTAL ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>⚖️ CHAMBER LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("Username")
        p = st.text_input("Password", type='password')
        if st.button("Access Engine", use_container_width=True):
            if u in USER_DB and p == USER_DB[u]["pwd"]:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.session_state['user_data'] = USER_DB[u]
                st.rerun()
            else:
                st.error("Authentication Failed. Invalid Credentials!")
else:
    # --- AUTO-TAX DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']

    with st.sidebar:
        st.header(f"👤 ADVOCATE AJAY")
        st.write(f"**Tier:** {u_data['plan']}")
        st.progress(min(u_data['used'] / u_data['limit'], 1.0))
        st.write(f"**Bulk Quota:** {u_data['used']} / {u_data['limit']}")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title("📊 Auto-Tax Bank Statement Auditor")
    st.markdown("Upload your Tally Masters and Bank PDF to auto-map bulk entries.")
    
    # --- ADVANCED INPUTS ---
    colA, colB = st.columns(2)
    with colA:
        tally_file = st.file_uploader("1. Sync Tally Masters (Excel)", type=['xlsx'])
    with colB:
        bank_pdf = st.file_uploader("2. Upload Bank Statement (PDF)", type=['pdf'])
    
    pdf_pwd = st.text_input("3. PDF Password (If protected)", type="password")

    # --- TALLY LEDGER LOGIC ---
    ledgers = []
    if tally_file:
        try:
            ld_df = pd.read_excel(tally_file)
            ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
            st.success(f"✅ Tally Sync Complete! {len(ledgers)} Ledgers loaded.")
        except Exception as e:
            st.error("Error reading Tally Excel. Please ensure ledgers are in the first column.")

    # --- BULK PROCESS EXECUTION ---
    if bank_pdf and st.button("🚀 Process Bulk Entries", use_container_width=True):
        
        if "gemini" not in st.secrets:
            st.error("System Error: API Key missing in Streamlit Secrets!")
        else:
            with st.spinner("AI is bypassing API limits and mapping ledgers..."):
                try:
                    # 1. API Configuration
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    
                    # --- SMART AUTO-FALLBACK MODEL SELECTOR ---
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    
                    target_model = None
                    # Priority 1: Try to find 1.5 Flash (Best for PDF)
                    for name in available_models:
                        if '1.5-flash' in name:
                            target_model = name
                            break
                    
                    # Priority 2: If Flash is missing, try 1.5 Pro
                    if not target_model:
                        for name in available_models:
                            if '1.5-pro' in name:
                                target_model = name
                                break
                    
                    # Priority 3: Fallback to ANY available Gemini model your key supports
                    if not target_model:
                        for name in available_models:
                            if 'gemini' in name:
                                target_model = name
                                break
                                
                    if not target_model:
                        st.error("❌ Critical Error: Your API Key is fully restricted. Please generate a new key at aistudio.google.com")
                        st.stop()
                        
                    model = genai.GenerativeModel(target_model)
                    st.info(f"Connected to dynamic model: {target_model}")
                    # ---------------------------------------------------------
                    
                    # 2. PDF Decryption
                    raw_bytes = bank_pdf.getvalue()
                    if pdf_pwd:
                        with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                            out = io.BytesIO()
                            pdf.save(out)
                            raw_bytes = out.getvalue()
                    
                    # 3. AI Extraction Prompt
                    audit_prompt = "Extract all bank transactions into a strict JSON list. Fields required: 'Date', 'Narration', 'Amount'. Output ONLY valid JSON without markdown formatting."
                    
                    response = model.generate_content([
                        {"mime_type": "application/pdf", "data": raw_bytes},
                        audit_prompt
                    ])
                    
                    # 4. JSON Processing & Auto-Mapping
                    if response.text:
                        clean_json = response.text.replace('```json', '').replace('```', '').strip()
                        df = pd.read_json(io.StringIO(clean_json))
                        
                        # ADVANCED FEATURE: Suspense Account Mapping Logic
                        def match_ledger(narration):
                            if not ledgers:
                                return "SUSPENSE ACCOUNT"
                            narr_upper = str(narration).upper()
                            for l in ledgers:
                                if l.upper() in narr_upper:
                                    return l
                            return "SUSPENSE ACCOUNT"
                        
                        df['Tally_Ledger'] = df['Narration'].apply(match_ledger)
                        st.session_state['user_data']['used'] += len(df)
                        
                        st.success(f"✅ Audit Successful! Auto-mapped {len(df)} bulk entries.")
                        st.dataframe(df, use_container_width=True)
                        
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Final XML/CSV for Tally", csv_data, "tally_bulk_import.csv", use_container_width=True)
                        
                except Exception as e:
                    # Agar purana model PDF direct upload support nahi karta, toh ye pakad lega
                    st.error(f"Engine Exception: {e}")
                    st.warning("Hint: If it says 'mime_type not supported', your current API key's model cannot read PDFs directly. You MUST generate a new API key.")
