import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- CACHED AI ENGINE SETUP ---
# Ye function sirf ek baar run hoga aur AI model ko memory mein save kar lega
@st.cache_resource
def load_ai_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def extract_transactions(model, pdf_bytes, prompt):
    try:
        response = model.generate_content([
            {"mime_type": "application/pdf", "data": pdf_bytes},
            prompt
        ])
        return response.text
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- SYSTEM DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 10000},
}

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Auto-Tax Pro Engine", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- SECURE LOGIN PORTAL ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>⚖️ CHAMBER LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        u = st.text_input("Username")
        p = st.text_input("Password", type='password')
        if st.button("Access BizOps Engine", use_container_width=True):
            if u in USER_DB and p == USER_DB[u]["pwd"]:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.session_state['user_data'] = USER_DB[u]
                st.rerun()
            else:
                st.error("Authentication Failed.")
else:
    # --- MAIN BIZOPS DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']

    with st.sidebar:
        st.header(f"Advocate {user.split('_')[1].capitalize()}")
        st.write(f"**Tier:** {u_data['plan']}")
        st.write(f"**Quota:** {u_data['used']} / {u_data['limit']}")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title("📊 Auto-Tax Bank Statement Auditor")
    st.markdown("Upload protected or open PDFs to extract Tally-ready JSON/CSV data.")
    
    bank_pdf = st.file_uploader("Select Bank PDF Document", type=['pdf'])
    pdf_pwd = st.text_input("Decryption Password (If applied)", type="password")

    if bank_pdf and st.button("🚀 Execute Audit", use_container_width=True):
        
        if "gemini" not in st.secrets:
            st.error("System Error: API Key missing in Streamlit Secrets.")
            st.stop()

        with st.spinner("Initializing AI Engine & Processing Document..."):
            try:
                # 1. Load Model via Cache
                ai_model = load_ai_model(st.secrets["gemini"]["api_key"])
                
                # 2. Handle PDF
                raw_bytes = bank_pdf.getvalue()
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO()
                        pdf.save(out)
                        raw_bytes = out.getvalue()

                # 3. Process Data
                audit_prompt = "Extract all bank transactions into a strict JSON list. Keys required: Date, Narration, Amount. Output ONLY the JSON."
                result = extract_transactions(ai_model, raw_bytes, audit_prompt)
                
                if result.startswith("ERROR"):
                    st.error(f"Engine Failure: {result}")
                else:
                    # 4. Clean & Display
                    clean_json = result.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean_json))
                    
                    # Update Usage Tracker
                    st.session_state['user_data']['used'] += len(df)
                    
                    st.success(f"Audit Successful! Processed {len(df)} transactions.")
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 Export for Tally (CSV)", df.to_csv(index=False).encode('utf-8'), "tally_import.csv", use_container_width=True)
                    
            except Exception as e:
                st.error(f"Critical System Exception: {e}")
