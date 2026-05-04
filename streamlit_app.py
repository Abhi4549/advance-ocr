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
st.set_page_config(page_title="BizOps Audit Engine", layout="wide")

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
        st.header(f"👤 {user.upper()}")
        st.write(f"**Tier:** {u_data['plan']}")
        st.progress(min(u_data['used'] / u_data['limit'], 1.0))
        st.write(f"**Quota:** {u_data['used']} / {u_data['limit']}")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title("📊 Auto-Tax Bank Statement Auditor")
    
    # File Uploaders
    bank_pdf = st.file_uploader("Upload Bank Statement (PDF)", type=['pdf'])
    pdf_pwd = st.text_input("PDF Password (Leave empty if no password)", type="password")

    if bank_pdf and st.button("🚀 Process Statement", use_container_width=True):
        
        # --- GEMINI API INTEGRATION START ---
        # 1. Sabse pehle API Key check karte hain
        if "gemini" not in st.secrets:
            st.error("System Error: API Key missing in Streamlit Secrets!")
        else:
            with st.spinner("AI Engine is auditing the document..."):
                try:
                    # 2. SDK Configure karna
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    
                    # 3. Stable Model Load karna
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 4. PDF Data Prepare karna
                    raw_bytes = bank_pdf.getvalue()
                    if pdf_pwd:
                        # Agar password hai, toh pehle usko unlock karo
                        with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                            out = io.BytesIO()
                            pdf.save(out)
                            raw_bytes = out.getvalue()
                    
                    # 5. API ko Document aur Prompt bhejna
                    audit_prompt = "Extract all transactions into a strict JSON list. Keys required: Date, Narration, Amount. Output ONLY the JSON."
                    response = model.generate_content([
                        {"mime_type": "application/pdf", "data": raw_bytes},
                        audit_prompt
                    ])
                    
                    # 6. Response ko CSV/Dataframe mein convert karna
                    if response.text:
                        # Extra text (jaise markdown backticks) ko clean karna
                        clean_json = response.text.replace('```json', '').replace('```', '').strip()
                        df = pd.read_json(io.StringIO(clean_json))
                        
                        # Quota update karna
                        st.session_state['user_data']['used'] += len(df)
                        
                        st.success(f"Audit Successful! Processed {len(df)} transactions.")
                        st.dataframe(df, use_container_width=True)
                        
                        # Download Button
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Export for Tally (CSV)", csv_data, "tally_import.csv", use_container_width=True)
                        
                except Exception as e:
                    st.error(f"Critical Engine Exception: {e}")
        # --- GEMINI API INTEGRATION END ---
