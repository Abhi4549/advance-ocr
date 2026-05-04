import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- 1. USER DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- 2. API ENGINE (STABLE v1) ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        # Check if secret exists first
        if "gemini" not in st.secrets:
            return "ERROR_API: Secret key 'gemini' not found in Streamlit settings."
        
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content([
            {"mime_type": "application/pdf", "data": pdf_bytes},
            prompt
        ])
        return response.text
    except Exception as e:
        return f"ERROR_AI: {str(e)}"

# --- 3. DASHBOARD UI ---
st.set_page_config(page_title="Suryavanshi Audit SaaS", layout="wide")

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 4. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        u = st.text_input("Username")
        p = st.text_input("Password", type='password')
        if st.button("Access Dashboard"):
            if u in USER_DB and p == USER_DB[u]["pwd"]:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.session_state['user_data'] = USER_DB[u]
                st.rerun()
            else:
                st.error("Invalid Username or Password!")
else:
    # --- 5. LOGGED IN DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']
    
    with st.sidebar:
        st.header(f"👤 {user.upper()}")
        st.write(f"Plan: **{u_data['plan']}**")
        st.write(f"Usage: {u_data['used']} / {u_data['limit']}")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title("🏆 Suryavanshi Audit Engine")
    
    tally_file = st.file_uploader("1. Sync Tally Excel", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Upload Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Optional)", type="password")

    if bank_pdf and st.button("🚀 Process Statement"):
        with st.spinner("AI is auditing..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                # Handle password if provided
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO(); pdf.save(out); raw_bytes = out.getvalue()

                # Audit Prompt
                prompt = "Extract all transactions into a JSON list: [{'Date': '...', 'Narration': '...', 'Amount': 0.0}]. ONLY JSON output."
                res = get_gemini_response(raw_bytes, prompt)
                
                if "ERROR_AI" in res or "ERROR_API" in res:
                    st.error(res)
                else:
                    clean = res.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean))
                    st.session_state['user_data']['used'] += len(df)
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), "audit.csv")

            except Exception as e:
                st.error(f"System Error: {e}")
