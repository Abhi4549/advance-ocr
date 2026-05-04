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
    
    # --- TABS FOR DIFFERENT FEATURES ---
    feature_tab1, feature_tab2 = st.tabs(["🏦 1. Bank Statement & Tally Sync", "📦 2. Bulk AI Bill Scanner"])

    # ==========================================
    # TAB 1: BANK STATEMENT PROCESSING
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
            except Exception as e:
                st.error("Error reading Tally Excel.")

        if bank_pdf and st.button("🚀 Process Bulk Entries", use_container_width=True):
            if "gemini" not in st.secrets:
                st.error("API Key missing in Streamlit Secrets!")
            else:
                status_box = st.empty()
                with st.spinner("AI is bypassing limits and auditing statement..."):
                    try:
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        # Using 1.5-flash for bulk performance
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        raw_bytes = bank_pdf.getvalue()
                        if pdf_pwd:
                            with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                                out = io.BytesIO()
                                pdf.save(out)
                                raw_bytes = out.getvalue()
                        
                        audit_prompt = """
                        Extract all bank transactions from this document. 
                        Return ONLY a valid JSON array.
                        Keys: "Date", "Narration", "Debit", "Credit".
                        Ensure plain numbers without commas.
                        """
                        
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
                                narr_upper = str(narration).upper()
                                for l in ledgers:
                                    if l.upper() in narr_upper: return l
                                return "SUSPENSE ACCOUNT"
                            
                            df['Tally_Ledger'] = df['Narration'].apply(match_ledger)
                            
                            # Save to memory for Tab 2
                            st.session_state['bank_data'] = df
                            st.session_state['user_data']['used'] += len(df)
                            
                            status_box.empty()
                            st.success(f"✅ Audit Successful! {len(df)} entries processed.")
                            
                            # Summary Metrics
                            t_deb = df['Debit'].sum()
                            t_cre = df['Credit'].sum()
                            st.markdown(f"**Total Debit:** ₹{t_deb:,.2f} | **Total Credit:** ₹{t_cre:,.2f} | **Balance:** ₹{t_cre-t_deb:,.2f}")
                            st.dataframe(df, use_container_width=True)
                            
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Download Tally CSV", csv_data, "bank_audit.csv", use_container_width=True)
                            
                    except Exception as e:
                        st.error(f"Engine Exception: {e}")

    # ==========================================
    # TAB 2: BULK AI BILL SCANNER (OCR & TRACKER)
    # ==========================================
    with feature_tab2:
        st.markdown("### 📦 Bulk Payment Audit (Verification)")
        st.write("Upload multiple bills to check if payments are recorded in the bank statement.")
        
        bill_type = st.radio("Invoice Type:", ["Purchase (I paid this)", "Sales (Customer paid me)"], horizontal=True)
        
        uploaded_bills = st.file_uploader("Upload Batch of Bills (Images/PDFs)", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
        
        if uploaded_bills and st.button("🔎 Batch Process All Bills", use_container_width=True):
            if "gemini" not in st.secrets:
                st.error("API Key missing!")
            elif st.session_state['bank_data'] is None:
                st.error("Please process Bank Statement in Tab 1 first!")
            else:
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                all_results = []
                prog_bar = st.progress(0)
                st_text = st.empty()
                
                for idx, b_file in enumerate(uploaded_bills):
                    try:
                        st_text.info(f"Scanning Bill {idx+1}/{len(uploaded_bills)}: {b_file.name}")
                        m_type = "application/pdf" if b_file.name.lower().endswith('pdf') else "image/jpeg"
                        
                        b_prompt = """Extract details. Return ONLY JSON: {"Party_Name": str, "Short_Name": str, "Total_Amount": float, "Inv_No": str}"""
                        
                        resp = model.generate_content(
                            [{"mime_type": m_type, "data": b_file.getvalue()}, b_prompt],
                            generation_config={"response_mime_type": "application/json"}
                        )
                        
                        if resp.text:
                            b_json = json.loads(resp.text)
                            amt = float(b_json.get('Total_Amount', 0))
                            s_name = b_json.get('Short_Name', '').upper()
                            
                            # Audit against memory
                            df_bank = st.session_state['bank_data']
                            search_col = 'Debit' if "Purchase" in bill_type else 'Credit'
                            
                            is_exact = not df_bank[df_bank[search_col] == amt].empty
                            is_name = not df_bank[df_bank['Narration'].str.upper().str.contains(s_name, na=False)].empty if s_name else False
                            
                            status = "✅ PAID" if is_exact else ("🔍 PARTIAL/NAME MATCH" if is_name else "❌ UNPAID")
                            
                            all_results.append({
                                "File Name": b_file.name,
                                "Party": b_json.get("Party_Name"),
                                "Amount": amt,
                                "Status": status
                            })
                        prog_bar.progress((idx + 1) / len(uploaded_bills))
                    except:
                        all_results.append({"File Name": b_file.name, "Status": "⚠️ ERROR"})

                st_text.success("Batch Audit Completed!")
                res_df = pd.DataFrame(all_results)
                
                # Color coding status
                def style_status(v):
                    c = 'green' if 'PAID' in v and 'PARTIAL' not in v else ('orange' if 'PARTIAL' in v else 'red')
                    return f'color: {c}; font-weight: bold'
                
                st.dataframe(res_df.style.applymap(style_status, subset=['Status']), use_container_width=True)
                
                csv_bulk = res_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Audit Report", csv_bulk, "bulk_audit_report.csv", use_container_width=True)
