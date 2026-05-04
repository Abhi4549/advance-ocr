import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import pikepdf

# --- 1. SIMPLE AUTH (Direct Match for Stability) ---
USER_DB = {
    "advocate_ajay": {"pwd": "admin123", "plan": "Platinum", "used": 0, "limit": 5000},
}

# --- 2. API ENGINE FIX ---
def get_gemini_response(pdf_bytes, prompt):
    try:
        if "gemini" in st.secrets:
            # Stable version configuration
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            # 'models/' prefix hata diya hai 404 fix karne ke liye
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
        st.error(f"API Error: {e}")
        return None

# --- 3. UI SETUP ---
st.set_page_config(page_title="Suryavanshi SaaS", layout="wide")
st.markdown("""<style>.stApp {background-color: #0e1117; color: white;} .stButton>button {background-color: #d4af37; color: black; font-weight: bold;}</style>""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #d4af37;'>🔐 SURYAVANSHI LOGIN</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        u = st.text_input("Username (advocate_ajay)")
        p = st.text_input("Password (admin123)", type='password')
        if st.button("Login"):
            # Simple direct check
            if u in USER_DB and p == USER_DB[u]["pwd"]:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.session_state['user_data'] = USER_DB[u]
                st.rerun()
            else:
                st.error("❌ Invalid Username or Password!")
else:
    # --- 4. DASHBOARD (AFTER LOGIN) ---
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

    tally_file = st.file_uploader("1. Sync Tally Masters (Excel)", type=['xlsx'])
    bank_pdf = st.file_uploader("2. Upload Bank PDF", type=['pdf'])
    pdf_pwd = st.text_input("3. PDF Password (Optional)", type="password")

    ledgers = []
    if tally_file:
        try:
            ld_df = pd.read_excel(tally_file)
            ledgers = ld_df.iloc[:, 0].dropna().astype(str).tolist()
            st.success("Tally Masters Synced!")
        except: st.error("Excel format error.")

    if bank_pdf and st.button("🚀 START AUDIT"):
        with st.spinner("AI is analyzing..."):
            try:
                raw_bytes = bank_pdf.getvalue()
                final_bytes = raw_bytes

                # Handle Password Protected PDFs
                if pdf_pwd:
                    with pikepdf.open(io.BytesIO(raw_bytes), password=pdf_pwd) as pdf:
                        out = io.BytesIO()
                        pdf.save(out)
                        final_bytes = out.getvalue()

                # Clean Prompt
                prompt = "Extract transactions as JSON list. Fields: Date, Narration, Amount. ONLY JSON output."
                res = get_gemini_response(final_bytes, prompt)
                
                if res:
                    clean = res.replace('```json', '').replace('```', '').strip()
                    df = pd.read_json(io.StringIO(clean))
                    
                    # Tally Matching
                    def match(n):
                        n = str(n).upper()
                        for l in ledgers:
                            if l.upper() in n: return l
                        return "SUSPENSE ACCOUNT"
                    
                    df['Ledger'] = df['Narration'].apply(match)
                    st.session_state['user_data']['used'] += len(df)
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 DOWNLOAD CSV", df.to_csv(index=False).encode('utf-8'), f"audit_{user}.csv")
            except Exception as e:
                st.error(f"Error: {e}")
