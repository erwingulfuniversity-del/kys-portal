import streamlit as st
import easyocr
import numpy as np
import cv2
from pdf2image import convert_from_path
from rapidfuzz import fuzz
import tempfile
import os
import re

# --- Constants for ICAO Doc 9303 (Passport Standard) ---
PASSPORT_LINE_LEN = 44
PASSPORT_LINES = 2

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

reader = load_ocr()

def is_valid_passport_standard(ocr_results):
    """
    Checks if the detected text contains a valid TD3 MRZ (Passport Standard).
    """
    # Look for lines that look like MRZ (long, mostly caps, numbers, and '<')
    mrz_lines = [res for res in ocr_results if len(res.replace(" ", "")) >= 40 and '<' in res]
    
    if len(mrz_lines) < 2:
        return False, "Standard Passport MRZ not detected."

    # Standard Passport (TD3) starts with 'P' and has specific lengths
    top_line = mrz_lines[-2].replace(" ", "")
    bottom_line = mrz_lines[-1].replace(" ", "")

    if not top_line.startswith('P'):
        return False, "Document detected is not a Passport (missing 'P' header)."
    
    # Check for typical MRZ character set (A-Z, 0-9, <)
    if not re.match(r'^[A-Z0-9<]+$', top_line) or not re.match(r'^[A-Z0-9<]+$', bottom_line):
        return False, "Document contains invalid characters for a standard passport."

    return True, "Valid Passport Standard Detected."

def process_document(pdf_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        tmp_path = tmp.name

    try:
        images = convert_from_path(tmp_path)
        img = np.array(images[0])
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # We need detail=0 for easy text joining, but we'll use it to find lines
        results = reader.readtext(img_bgr, detail=0)
        return results
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- UI ---
st.title("🎓 Smart KYS Student Portal")

with st.form("kys_form"):
    st.subheader("1. Enter Personal Details")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name (as on Passport)")
        dob = st.text_input("DOB (YYMMDD)")
    with col2:
        country = st.text_input("Country Code (e.g., GBR, USA)")
        uploaded_file = st.file_uploader("Upload Passport PDF", type=["pdf"])

    submit = st.form_submit_button("Verify Passport")

if submit:
    if uploaded_file:
        with st.spinner("Analyzing document structure..."):
            ocr_lines = process_document(uploaded_file)
            full_text = " ".join(ocr_lines).upper()

            # STAGE 1: Standard Check (Is it a passport?)
            is_passport, message = is_valid_passport_standard(ocr_lines)
            
            if not is_passport:
                st.error(f"❌ Verification Blocked: {message}")
                st.warning("Please upload a valid International Passport. Identity cards or licenses are not accepted.")
            else:
                # STAGE 2: Data Matching
                name_score = fuzz.partial_ratio(name.upper(), full_text)
                name_match = name_score > 80
                dob_match = dob in full_text
                country_match = country.upper() in full_text

                if name_match and dob_match and country_match:
                    st.success("✅ Standard Passport Verified & Student Data Matched!")
                else:
                    st.error("❌ Passport format is correct, but details do not match.")
                    st.info(f"Check: Name({name_match}), DOB({dob_match}), Country({country_match})")
