import streamlit as st
from passporteye import read_mrz
from difflib import SequenceMatcher
from PIL import Image
import tempfile
import os

# --- Page Configuration ---
st.set_page_config(page_title="KYS Student Verifier", page_icon="🛂")

def fuzzy_match(string1, string2):
    if not string1 or not string2:
        return 0
    return SequenceMatcher(None, string1.upper(), string2.upper()).ratio()

def verify_logic(file_path, input_name, input_dob, input_country):
    mrz = read_mrz(file_path)
    if mrz is None:
        return False, "Passport MRZ not detected. Please upload a clearer scan.", 0
    
    data = mrz.to_dict()
    
    # Extract data from MRZ
    p_name = f"{data.get('names', '')} {data.get('surname', '')}"
    p_dob = data.get('date_of_birth', '')
    p_country = data.get('country', '')

    # Matching Logic
    name_score = fuzzy_match(input_name, p_name)
    name_verified = name_score > 0.8
    dob_verified = (input_dob == p_dob)
    country_verified = (input_country.upper() == p_country.upper())

    if name_verified and dob_verified and country_verified:
        return True, "Identity Verified Successfully!", name_score
    else:
        errors = []
        if not name_verified: errors.append("Name mismatch")
        if not dob_verified: errors.append("DOB mismatch")
        if not country_verified: errors.append("Country mismatch")
        return False, f"Verification Failed: {', '.join(errors)}", name_score

# --- UI Layout ---
st.title("🎓 Student Portal: KYS Verification")
st.write("Complete your registration by verifying your international passport.")

with st.sidebar:
    st.header("Help & Instructions")
    st.info("""
    - **Name:** Enter full name as on ID.
    - **DOB:** Must be in **YYMMDD** format (e.g., 950520).
    - **Country:** 3-letter ISO code (e.g., GBR, USA, IND).
    """)

# Input Fields
col1, col2 = st.columns(2)
with col1:
    user_name = st.text_input("Full Name")
    user_dob = st.text_input("Date of Birth (YYMMDD)", help="Example: Jan 20, 1998 -> 980120")

with col2:
    user_country = st.text_input("Country Code (3 letters)")
    uploaded_file = st.file_uploader("Upload Passport (Image/PDF)", type=['jpg', 'jpeg', 'png', 'pdf'])

# Verification Trigger
if st.button("Run Verification", use_container_width=True):
    if uploaded_file and user_name and user_dob and user_country:
        # Save uploaded file to a temporary location for PassportEye to read
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        with st.spinner("Analyzing Passport..."):
            is_valid, message, score = verify_logic(tmp_path, user_name, user_dob, user_country)
        
        # Clean up temp file
        os.remove(tmp_path)

        # Display Results
        if is_valid:
            st.success(message)
            st.metric("Match Confidence", f"{score*100:.1f}%")
            st.balloons()
        else:
            st.error(message)
            st.warning(f"Note: Your name matched with {score*100:.1f}% confidence.")
    else:
        st.warning("Please fill in all details and upload your passport.")
