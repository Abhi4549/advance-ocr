import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- LOGIN DATABASE ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- API FUNCTION ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        # Step 1: Config
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        # Step 2: Model (Stable v1)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Step 3: Call
        response = model.generate_content([
            {"mime_type": "application/pdf", "data": pdf_bytes},
            prompt
        ])
        return response.text
    except Exception as e:
        return f"ERROR_AI: {str(e)}"

# --- UI CONFIG ---
st.set_page_config(page_title="Suryavanshi Audit", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type='password')
    if st.button("Login"):
        if u in USER_DB and p == USER_DB[u]["pwd"]:
            st.session_state['logged_in'] = True
            st.session_state['user'] = u
            st.session_state['user_data'] = USER_DB[u]
            st.rerun()
        else:
            st.error("Invalid credentials")

# --- MAIN APP ---
else:
    user = st.session_state['user']
    u_data = st.session_state['user_data']

    st.sidebar.title(f"Welcome {user}")
    st.sidebar.write(f"Usage: {u_data['used']} / {u_data['limit']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.header("📊 Bank Statement Auditor")
    
    tally_file = st.file_uploader("Upload Tally Excel", type=['xlsx'])
    bank_pdf = st.file_uploader("Upload Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("PDF Password (Optional)", type="password")

    if bank_pdf and st.button("🚀 Process"):
        with st.spinner("Processing..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                # Password handling
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO(); pdf.save(out); raw_bytes = out.getvalue()
                
                # Prompt
                prompt = "Extract all transactions into a JSON list with keys: Date, Narration, Amount. Return ONLY JSON."
                res = get_gemini_response(raw_bytes, prompt)
                
                if "ERROR_AI" in res:
                    st.error(res)
                else:
                    # Clean & Load
                    clean_res = res.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean_res))
                    
                    # Update count
                    st.session_state['user_data']['used'] += len(df)
                    st.success(f"Extracted {len(df)} rows.")
                    st.dataframe(df)
                    
            except Exception as e:
                st.error(f"App Error: {e}")
