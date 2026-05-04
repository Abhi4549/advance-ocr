import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf
import hashlib

# --- 1. SECURE AUTH ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

USER_DB = {
    "advocate_ajay": {"pwd": make_hashes("admin123"), "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- 2. THE FINAL API FIX ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        if "gemini" in st.secrets:
            # Forcefully using v1 API setup
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            
            # Version 404 fix: Directly calling the model without 'models/' prefix
            # This is the standard way for v1 stable API
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            response = model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_bytes},
                prompt
            ])
            return response.text
        else:
            st.error("API Key missing in Secrets!")
            return None
    except Exception as e:
        # If it still fails, it's likely a library version mismatch on Streamlit's end
        st.error(f"API Error: {e}")
        return None

# --- 3. UI SETUP ---
st.set_page_config(page_title="Suryavanshi SaaS", layout="wide")
st.markdown("""<style>.stApp {background-color: #0e1117; color: white;} .stButton>button {background-color: #d4af37; color: black; font-weight: bold;}</style>""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 SURYAVANSHI LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u = st.text_input("Username")
        p = st.text_input("Password", type='password')
        if st.button("Login"):
            if u in USER_DB and check_hashes(p, USER_DB[u]["pwd"]):
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.session_state['user_data'] = USER_DB[u]
                st.rerun()
            else: st.error("Galat hai!")
else:
    # --- 4. DASHBOARD ---
    user = st.session_state['user']
    u_data = st.session_state['user_data']
    
    with st.sidebar:
        st.markdown(f"### 👤 {user.upper()}")
        st.write(f"**Plan:** {u_data['plan']}")
        st.progress(u_data['used'] / u_data['limit'])
        st.write(f"Usage: {u_data['used']} / {u_data['limit']}")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown(f"<h2 style='color: #d4af37;'>🏆 {user.upper()}'S AUDIT ENGINE</h2>", unsafe_allow_html=True)

    tally_file = st.file_uploader("1. Excel Masters", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Optional)", type="password")

    ledgers = []
    if tally_file:
        ld_df = pd.read_excel(tally_file)
        ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()

    if bank_pdf and st.button("🚀 START AUDIT"):
        with st.spinner("AI is working..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                final_bytes = raw_bytes

                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO(); pdf.save(out); final_bytes = out.getvalue()

                # Optimized Prompt
                prompt = "Extract transactions as JSON: [{'Date': '...', 'Narration': '...', 'Amount': 0.0}]"
                res = get_gemini_response(final_bytes, prompt)
                
                if res:
                    clean = res.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean))
                    
                    def match(n):
                        n = str(n).upper()
                        for l in ledgers:
                            if l.upper() in n: return l
                        return "SUSPENSE ACCOUNT"
                    
                    df['Ledger'] = df['Narration'].apply(match)
                    st.session_state['user_data']['used'] += len(df)
                    st.dataframe(df)
                    st.download_button("📥 DOWNLOAD CSV", df.to_csv(index=False).encode('utf-8'), "audit.csv")
            except Exception as e:
                st.error(f"Error: {e}")
