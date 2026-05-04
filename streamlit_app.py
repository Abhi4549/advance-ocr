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

    st.title("📊 BizOps Auto-Tax & Master Auditor")
    
    tab1, tab2 = st.tabs(["🏦 1. Bank Statement & Tally Sync", "📦 2. Bulk Audit (Bills/Excel)"])

    # ==========================================
    # TAB 1: BANK STATEMENT & TALLY SYNC
    # ==========================================
    with tab1:
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
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        target_model = next((m for m in available_models if 'flash' in m), available_models[0])
                        model = genai.GenerativeModel(target_model)
                        
                        raw_bytes = bank_pdf.getvalue()
                        if pdf_pwd:
                            with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                                out = io.BytesIO(); pdf.save(out); raw_bytes = out.getvalue()
                        
                        audit_prompt = "Extract transactions. Return ONLY JSON array. Keys: 'Date', 'Narration', 'Debit', 'Credit'."
                        response = model.generate_content([{"mime_type": "application/pdf", "data": raw_bytes}, audit_prompt],
                                                         generation_config={"response_mime_type": "application/json"})
                        
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
                            
                            # Metrics Dashboard
                            c1, c2, c3 = st.columns(3)
                            c1.metric("🔴 Total Debit", f"₹ {df['Debit'].sum():,.2f}")
                            c2.metric("🟢 Total Credit", f"₹ {df['Credit'].sum():,.2f}")
                            c3.metric("🏦 Balance", f"₹ {(df['Credit'].sum() - df['Debit'].sum()):,.2f}")
                            
                            st.dataframe(df, use_container_width=True)
                            st.download_button("📥 Download Tally CSV", df.to_csv(index=False).encode('utf-8'), "bank_audit.csv")
                    except Exception as e: st.error(f"Engine Exception: {e}")

    # ==========================================
    # TAB 2: MASTER BULK AUDIT (BILLS & EXCEL)
    # ==========================================
    with tab2:
        st.markdown("### 📦 Bulk Audit (Verify Payments/Receipts)")
        audit_mode = st.radio("Audit Type:", ["Purchase (Payment I made)", "Sales (Payment I received)"], horizontal=True)
        
        col1, col2 = st.columns(2)
        with col1:
            tally_excel = st.file_uploader("Option A: Upload Tally Outstanding Excel", type=['xlsx'])
        with col2:
            uploaded_bills = st.file_uploader("Option B: Upload Batch of Bills", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
        
        if (tally_excel or uploaded_bills) and st.button("🔎 Start Bulk Audit", use_container_width=True):
            if st.session_state['bank_data'] is None:
                st.error("Pehle Tab 1 process karein!")
            else:
                df_bank = st.session_state['bank_data']
                search_col = 'Debit' if "Purchase" in audit_mode else 'Credit'
                all_results = []

                # Part A: Excel Audit
                if tally_excel:
                    with st.spinner("Analyzing Excel rows..."):
                        try:
                            ext_df = pd.read_excel(tally_excel)
                            for _, row in ext_df.iterrows():
                                p_name = str(row.iloc[0]).upper()
                                amt = pd.to_numeric(row.iloc[1], errors='coerce') or 0
                                is_ex = not df_bank[df_bank[search_col] == amt].empty
                                is_nm = not df_bank[df_bank['Narration'].str.upper().str.contains(p_name[:5], na=False)].empty
                                stat = "✅ PAID" if is_ex else ("🔍 PARTIAL" if is_nm else "❌ UNPAID")
                                all_results.append({"Source": "Excel", "Party": p_name, "Amount": amt, "Status": stat})
                        except: st.error("Excel format error.")

                # Part B: Bills Audit
                if uploaded_bills:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    target_model = next((m for m in available_models if 'flash' in m), available_models[0])
                    model = genai.GenerativeModel(target_model)
                    
                    prog = st.progress(0)
                    for idx, b_file in enumerate(uploaded_bills):
                        try:
                            m_type = "application/pdf" if b_file.name.lower().endswith('pdf') else "image/jpeg"
                            b_prompt = 'Extract: {"Party_Name": str, "Short_Name": str, "Total_Amount": float}'
                            resp = model.generate_content([{"mime_type": m_type, "data": b_file.getvalue()}, b_prompt],
                                                         generation_config={"response_mime_type": "application/json"})
                            bj = json.loads(resp.text)
                            amt = float(bj.get('Total_Amount', 0))
                            sn = bj.get('Short_Name', '').upper()
                            is_ex = not df_bank[df_bank[search_col] == amt].empty
                            is_nm = not df_bank[df_bank['Narration'].str.upper().str.contains(sn, na=False)].empty if sn else False
                            stat = "✅ PAID" if is_ex else ("🔍 PARTIAL" if is_nm else "❌ UNPAID")
                            all_results.append({"Source": b_file.name, "Party": bj.get("Party_Name"), "Amount": amt, "Status": stat})
                            prog.progress((idx + 1) / len(uploaded_bills))
                        except: all_results.append({"Source": b_file.name, "Status": "⚠️ ERROR"})

                if all_results:
                    st.success("Bulk Audit Complete!")
                    res_df = pd.DataFrame(all_results)
                    def style_status(v):
                        c = 'green' if 'PAID' in v and 'PARTIAL' not in v else ('orange' if 'PARTIAL' in v else 'red')
                        return f'color: {c}; font-weight: bold'
                    st.dataframe(res_df.style.applymap(style_status, subset=['Status']), use_container_width=True)
                    st.download_button("📥 Download Final Audit Report", res_df.to_csv(index=False), "master_audit.csv")
