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
if 'bank_data' not in st.session_state:
    st.session_state['bank_data'] = None

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
            st.session_state.clear()
            st.rerun()

    st.title("📊 BizOps Auto-Tax & Bulk Bill Scanner")
    
    feature_tab1, feature_tab2 = st.tabs(["🏦 1. Bank Statement & Tally Sync", "📦 2. Bulk AI Bill Scanner"])

    # ==========================================
    # TAB 1: BANK AUDIT (DYNAMIC MODEL FIX)
    # ==========================================
    with feature_tab1:
        st.markdown("### Bank Audit & Tally Ledger Mapping")
        colA, colB = st.columns(2)
        with colA:
            tally_file = st.file_uploader("Sync Tally Masters (Excel)", type=['xlsx'])
        with colB:
            bank_pdf = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])
        
        pdf_pwd = st.text_input("PDF Password (If protected)", type="password")

        ledgers = []
        if tally_file:
            try:
                ld_df = pd.read_excel(tally_file)
                ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
                st.success(f"✅ Tally Sync Complete! {len(ledgers)} Ledgers loaded.")
            except: st.error("Error reading Tally Excel.")

        if bank_pdf and st.button("🚀 Process Bulk Entries", use_container_width=True):
            if "gemini" not in st.secrets:
                st.error("API Key missing!")
            else:
                status_box = st.empty()
                with st.spinner("AI is bypassing limits..."):
                    try:
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        
                        # --- DYNAMIC MODEL SELECTOR (THE FIX) ---
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        target_model = next((m for m in available_models if 'flash' in m), available_models[0])
                        model = genai.GenerativeModel(target_model)
                        st.info(f"Connected to: {target_model}")
                        
                        raw_bytes = bank_pdf.getvalue()
                        if pdf_pwd:
                            with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                                out = io.BytesIO()
                                pdf.save(out); raw_bytes = out.getvalue()
                        
                        audit_prompt = "Extract bank transactions. Return ONLY JSON array. Keys: 'Date', 'Narration', 'Debit', 'Credit'."
                        
                        response = model.generate_content(
                            [{"mime_type": "application/pdf", "data": raw_bytes}, audit_prompt],
                            generation_config={"response_mime_type": "application/json"}
                        )
                        
                        if response.text:
                            df = pd.DataFrame(json.loads(response.text))
                            df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
                            df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                            
                            def match_ledger(narration):
                                if not ledgers: return "SUSPENSE ACCOUNT"
                                for l in ledgers:
                                    if l.upper() in str(narration).upper(): return l
                                return "SUSPENSE ACCOUNT"
                            
                            df['Tally_Ledger'] = df['Narration'].apply(match_ledger)
                            st.session_state['bank_data'] = df
                            st.session_state['user_data']['used'] += len(df)
                            
                            status_box.empty()
                            st.success(f"✅ Audit Successful! {len(df)} entries.")
                            st.dataframe(df, use_container_width=True)
                            
                    except Exception as e:
                        st.error(f"Engine Exception: {e}")

    # ==========================================
    # TAB 2: BULK BILL SCANNER (DYNAMIC MODEL FIX)
    # ==========================================
    with feature_tab2:
        st.markdown("### 📦 Bulk Payment Audit")
        bill_type = st.radio("Invoice Type:", ["Purchase (I paid)", "Sales (I received)"], horizontal=True)
        uploaded_bills = st.file_uploader("Upload Batch", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
        
        if uploaded_bills and st.button("🔎 Batch Process", use_container_width=True):
            if st.session_state['bank_data'] is None:
                st.error("Pehle Tab 1 process karein!")
            else:
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                
                # Dynamic Model Fix for Tab 2
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = next((m for m in available_models if 'flash' in m), available_models[0])
                model = genai.GenerativeModel(target_model)
                
                all_results = []
                prog = st.progress(0)
                for idx, b_file in enumerate(uploaded_bills):
                    try:
                        m_type = "application/pdf" if b_file.name.lower().endswith('pdf') else "image/jpeg"
                        b_prompt = 'Extract details. Return ONLY JSON: {"Party_Name": str, "Short_Name": str, "Total_Amount": float}'
                        
                        resp = model.generate_content(
                            [{"mime_type": m_type, "data": b_file.getvalue()}, b_prompt],
                            generation_config={"response_mime_type": "application/json"}
                        )
                        
                        if resp.text:
                            bj = json.loads(resp.text)
                            amt = float(bj.get('Total_Amount', 0))
                            sn = bj.get('Short_Name', '').upper()
                            
                            db = st.session_state['bank_data']
                            col = 'Debit' if "Purchase" in bill_type else 'Credit'
                            
                            is_ex = not db[db[col] == amt].empty
                            is_nm = not db[db['Narration'].str.upper().str.contains(sn, na=False)].empty if sn else False
                            stat = "✅ PAID" if is_ex else ("🔍 PARTIAL" if is_nm else "❌ UNPAID")
                            
                            all_results.append({"File": b_file.name, "Party": bj.get("Party_Name"), "Amount": amt, "Status": stat})
                        prog.progress((idx + 1) / len(uploaded_bills))
                    except: all_results.append({"File": b_file.name, "Status": "⚠️ ERROR"})

                st.dataframe(pd.DataFrame(all_results), use_container_width=True)
