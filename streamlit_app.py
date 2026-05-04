import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf
import json

# --- CHAMBER LOGIN DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 10000},
}

# --- UI CONFIGURATION ---
st.set_page_config(page_title="BizOps Auto-Tax Engine", layout="wide")

# --- SAFE MEMORY INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = "guest"
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = {"pwd": "", "plan": "Platinum", "used": 0, "limit": 10000}

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
        st.header(f"👤 {user.upper()}")
        st.write(f"**Tier:** {u_data['plan']}")
        st.progress(min(u_data['used'] / u_data['limit'], 1.0))
        st.write(f"**Bulk Quota:** {u_data['used']} / {u_data['limit']}")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['user'] = "guest"
            st.session_state['user_data'] = {"pwd": "", "plan": "Platinum", "used": 0, "limit": 10000}
            st.rerun()

    st.title("📊 Auto-Tax Bank Statement Auditor")
    st.markdown("Upload your Tally Masters and Bank PDF to auto-map bulk entries.")
    
    colA, colB = st.columns(2)
    with colA:
        tally_file = st.file_uploader("1. Sync Tally Masters (Excel)", type=['xlsx'])
    with colB:
        bank_pdf = st.file_uploader("2. Upload Bank Statement (PDF)", type=['pdf'])
    
    pdf_pwd = st.text_input("3. PDF Password (If protected)", type="password")

    ledgers = []
    if tally_file:
        try:
            ld_df = pd.read_excel(tally_file)
            ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
            st.success(f"✅ Tally Sync Complete! {len(ledgers)} Ledgers loaded.")
        except Exception as e:
            st.error("Error reading Tally Excel. Please ensure ledgers are in the first column.")

    if bank_pdf and st.button("🚀 Process Bulk Entries", use_container_width=True):
        
        if "gemini" not in st.secrets:
            st.error("System Error: API Key missing in Streamlit Secrets!")
        else:
            status_box = st.empty()
            
            with st.spinner("Processing Statement... Please wait up to 60 seconds."):
                try:
                    status_box.info("Step 1: Connecting to AI Engine...")
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    target_model = None
                    for name in available_models:
                        if '1.5-flash' in name or '2.5-flash' in name:
                            target_model = name
                            break
                    if not target_model:
                        for name in available_models:
                            if '1.5-pro' in name:
                                target_model = name
                                break
                    if not target_model:
                        for name in available_models:
                            if 'gemini' in name:
                                target_model = name
                                break
                                
                    if not target_model:
                        st.error("❌ Critical Error: Your API Key is fully restricted.")
                        st.stop()
                        
                    model = genai.GenerativeModel(target_model)
                    status_box.warning(f"Step 2: Model '{target_model}' Connected. Reading PDF Data...")
                    
                    raw_bytes = bank_pdf.getvalue()
                    if pdf_pwd:
                        with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                            out = io.BytesIO()
                            pdf.save(out)
                            raw_bytes = out.getvalue()
                    
                    # STRICT JSON PROMPT FOR DEBIT/CREDIT
                    audit_prompt = """
                    Extract all bank transactions from this document. 
                    You MUST return ONLY a valid JSON array.
                    Each object in the array MUST have strictly these four keys: "Date", "Narration", "Debit", "Credit".
                    If a transaction is a withdrawal/money out, put the amount in "Debit" and 0 in "Credit".
                    If a transaction is a deposit/money in, put the amount in "Credit" and 0 in "Debit".
                    Ensure amounts are plain numbers without currency symbols or commas.
                    """
                    
                    status_box.warning("Step 3: AI is extracting transactions... Please do not refresh.")
                    
                    response = model.generate_content(
                        [{"mime_type": "application/pdf", "data": raw_bytes}, audit_prompt],
                        generation_config={"response_mime_type": "application/json"}
                    )
                    
                    status_box.success("Step 4: Data Extracted! Organizing and Mapping to Tally Ledgers...")
                    
                    if response.text:
                        raw_data = json.loads(response.text)
                        df = pd.DataFrame(raw_data)
                        
                        # Data Cleaning
                        df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
                        df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                        
                        # --- NEW FEATURE: STATS CALCULATION ---
                        total_entries = len(df)
                        total_debit = df['Debit'].sum()
                        total_credit = df['Credit'].sum()
                        net_balance = total_credit - total_debit
                        
                        # Ledger Mapping
                        def match_ledger(narration):
                            if not ledgers:
                                return "SUSPENSE ACCOUNT"
                            narr_upper = str(narration).upper()
                            for l in ledgers:
                                if l.upper() in narr_upper:
                                    return l
                            return "SUSPENSE ACCOUNT"
                        
                        df['Tally_Ledger'] = df['Narration'].apply(match_ledger)
                        
                        # Split DataFrames for UI
                        df_debit = df[df['Debit'] > 0].copy()
                        df_credit = df[df['Credit'] > 0].copy()
                        
                        st.session_state['user_data']['used'] += total_entries
                        status_box.empty()
                        
                        st.success("✅ Audit Successful!")
                        
                        # --- TOP METRICS DASHBOARD ---
                        st.markdown("### 📈 Statement Summary")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("📝 Total Entries", total_entries)
                        c2.metric("🔴 Total Debit (Out)", f"₹ {total_debit:,.2f}")
                        c3.metric("🟢 Total Credit (In)", f"₹ {total_credit:,.2f}")
                        c4.metric("🏦 Net Balance", f"₹ {net_balance:,.2f}")
                        
                        st.markdown("---")
                        
                        # --- DISPLAY TABS ---
                        tab1, tab2, tab3 = st.tabs(["🔴 Debit Details", "🟢 Credit Details", "📊 Full Tally Data"])
                        
                        with tab1:
                            st.dataframe(df_debit[['Date', 'Narration', 'Debit', 'Tally_Ledger']], use_container_width=True)
                            
                        with tab2:
                            st.dataframe(df_credit[['Date', 'Narration', 'Credit', 'Tally_Ledger']], use_container_width=True)
                            
                        with tab3:
                            st.dataframe(df, use_container_width=True)
                        
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Final CSV for Tally", csv_data, "tally_bulk_import.csv", use_container_width=True)
                        
                except Exception as e:
                    status_box.empty()
                    st.error(f"Engine Exception: {e}")
