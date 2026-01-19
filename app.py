import streamlit as st
import math
import pandas as pd
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials

# ======================================================
# 🔐 EMAIL ACCESS CONTROL (OFFICE ONLY)
# ======================================================
user = st.experimental_user

if not user or not user.email:
    st.error("❌ Please sign in to continue.")
    st.stop()

allowed_emails = st.secrets["auth"]["allowed_emails"]

if user.email not in allowed_emails:
    st.error("🚫 Access Denied")
    st.write("This tool is restricted to authorized Manohar Chai office emails only.")
    st.write(f"Signed in as: {user.email}")
    st.stop()

# ======================================================
# 🎨 BRAND + MOBILE UI (MANOHAR CHAI – RED THEME)
# ======================================================
st.set_page_config(
    page_title="Manohar Chai – Franchise Distance Tool",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 0.5rem;
    padding-bottom: 1rem;
}

/* Brand box */
.brand-box {
    background: #b71c1c;
    padding: 14px;
    border-radius: 14px;
    margin-bottom: 15px;
}

/* Brand text */
.brand-title {
    color: white;
    font-size: 26px;
    font-weight: 900;
    letter-spacing: 1px;
}

.brand-sub {
    color: #ffebee;
    font-size: 13px;
    margin-top: 2px;
}

/* Mobile input */
input {
    font-size: 16px !important;
}

/* Button */
.stButton button {
    background-color: #b71c1c;
    color: white;
    font-weight: bold;
    border-radius: 10px;
    height: 48px;
}

.stButton button:hover {
    background-color: #8e0000;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# ☕ BRAND HEADER (LOGO + TEXT)
# ======================================================
col1, col2 = st.columns([1, 3])

with col1:
    st.image("ManoharLogo_Social.png", width=90)

with col2:
    st.markdown("""
    <div class="brand-box">
        <div class="brand-title">MANOHAR CHAI</div>
        <div class="brand-sub">
            Franchise Distance Calculator · Internal Office Use Only
        </div>
    </div>
    """, unsafe_allow_html=True)

# ======================================================
# 📍 USER INPUT (LAT/LONG OR GOOGLE MAPS LINK)
# ======================================================
st.subheader("📍 Enter Location")

location_input = st.text_input(
    "Paste Lat,Long OR Google Maps link",
    placeholder="22.05762,78.93807  OR  https://maps.google.com/..."
)

run = st.button("🔍 Calculate Distance", use_container_width=True)

# ======================================================
# 🧠 INPUT PARSER
# ======================================================
def extract_lat_lng(text):
    if not text:
        return None, None

    # Case 1: lat,long
    m = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Case 2: Google Maps link
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None, None

# ======================================================
# 🔐 GOOGLE SHEET AUTH (PRIVATE)
# ======================================================
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

# ======================================================
# 📊 LOAD GOOGLE SHEET
# ======================================================
SHEET_ID = "1VNVTYE13BEJ2-P0klp5vI7XdPRd0poZujIyNQuk-nms"
sheet = gc.open_by_key(SHEET_ID)

franchise_df = pd.DataFrame(
    sheet.worksheet("Franchise_Summary").get_all_records()
)

# ======================================================
# 📍 LAT/LONG FROM SHEET
# ======================================================
def extract_lat_lon(df):
    for col in df.columns:
        if df[col].astype(str).str.contains(r'^-?\d+\.\d+,\s*-?\d+\.\d+$').any():
            sp = df[col].astype(str).str.split(",", expand=True)
            df["Latitude"] = pd.to_numeric(sp[0], errors="coerce")
            df["Longitude"] = pd.to_numeric(sp[1], errors="coerce")
            df["Lat_Long"] = df[col]
            break
    return df

franchise_df = extract_lat_lon(franchise_df)

# ======================================================
# 📐 HAVERSINE DISTANCE
# ======================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ======================================================
# 🚀 MAIN LOGIC
# ======================================================
if run:
    user_lat, user_lng = extract_lat_lng(location_input)

    if user_lat is None or user_lng is None:
        st.error("❌ Invalid input. Paste Lat,Long or Google Maps link.")
        st.stop()

    results = []

    for _, fr in franchise_df.iterrows():
        if pd.isna(fr["Latitude"]) or pd.isna(fr["Longitude"]):
            continue

        dist = haversine(user_lat, user_lng, fr["Latitude"], fr["Longitude"])

        map_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={user_lat},{user_lng}"
            f"&destination={fr['Lat_Long']}"
            "&travelmode=walking"
        )

        results.append({
            "PARTY NAME": fr.get("PARTY NAME", ""),
            "ADDRESS": fr.get("ADDRESS", ""),
            "KM": round(dist, 2),
            "VIEW ROUTE": map_url,
            "LAT_LONG": fr["Lat_Long"]
