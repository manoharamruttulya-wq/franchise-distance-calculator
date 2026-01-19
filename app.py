import streamlit as st
import pandas as pd
import math
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Franchise Distance Checker", layout="wide")
st.title("📍 Franchise Distance Checker")

RADIUS_LIMIT = st.slider("Radius Limit (KM)", 0.5, 5.0, 1.3, 0.1)

# ---- Google Auth via Secrets ----
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = {
    "type": st.secrets["gcp"]["type"],
    "project_id": st.secrets["gcp"]["project_id"],
    "private_key_id": st.secrets["gcp"]["private_key_id"],
    "private_key": st.secrets["gcp"]["private_key"].replace("\\n", "\n"),
    "client_email": st.secrets["gcp"]["client_email"],
    "client_id": st.secrets["gcp"]["client_id"],
    "auth_uri": st.secrets["gcp"]["auth_uri"],
    "token_uri": st.secrets["gcp"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["gcp"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["gcp"]["client_x509_cert_url"],
}

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

SHEET_ID = "1VNVTYE13BEJ2-P0klp5vI7XdPRd0poZujIyNQuk-nms"
sheet = gc.open_by_key(SHEET_ID)

franchise_df = pd.DataFrame(sheet.worksheet("Franchise_Summary").get_all_records())
check_df = pd.DataFrame(sheet.worksheet("Check_Location").get_all_records())

st.success("Sheet Loaded Successfully ✅")
st.dataframe(check_df, use_container_width=True)
