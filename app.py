import streamlit as st
import math
import pandas as pd
import gspread
import re
import requests
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Manohar Chai – Franchise Distance Tool",
    layout="wide"
)

# ===============================
# CSS (SAFE, NO BLANK)
# ===============================
st.markdown("""
<style>
.block-container {
    max-width: 1100px;
    padding-top: 1rem;
}

.mc-header {
    display: flex;
    align-items: center;
    gap: 14px;
}

.mc-logo img {
    height: 56px;
}

.mc-title {
    font-size: 30px;
    font-weight: 900;
}
.mc-title .red { color: #b71c1c; }

.mc-sub {
    font-size: 13px;
    color: #666;
}

.stButton button {
    background-color: #b71c1c;
    color: white;
    font-weight: 700;
    border-radius: 12px;
    height: 52px;
    font-size: 16px;
}
.stButton button:hover { background-color: #8e0000; }

@media (max-width: 768px) {
    .mc-header { flex-direction: column; text-align: center; }
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 2 CM TOP SPACER
# ===============================
st.markdown("<div style='height:76px'></div>", unsafe_allow_html=True)

# ===============================
# HEADER
# ===============================
st.markdown("""
<div class="mc-header">
    <div class="mc-logo">
        <img src="https://raw.githubusercontent.com/manoharamruttulya-wq/franchise-distance-calculator/main/ManoharLogo_Social.png">
    </div>
    <div>
        <div class="mc-title"><span class="red">MANOHAR</span> CHAI</div>
        <div class="mc-sub">Franchise Distance Calculator · Internal Office Use Only</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)

# ===============================
# INPUT
# ===============================
st.subheader("📍 Enter Location")

location_input = st.text_input(
    "Paste Lat,Long OR Google Maps link",
    placeholder="22.05762,78.93807  OR  https://maps.app.goo.gl/..."
)

run = st.button("🔍 Calculate Distance", use_container_width=True)

# ===============================
# HELPERS
# ===============================
def extract_lat_lng(text):
    if not text:
        return None, None

    # Expand short links (maps.app.goo.gl)
    if "maps.app.goo.gl" in text:
        try:
            r = requests.get(text, allow_redirects=True, timeout=10)
            text = r.url
        except:
            return None, None

    # lat,long
    m = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # @lat,long
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # ll=lat,long
    m = re.search(r'[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # !3dlat!4dlong
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ===============================
# GOOGLE SHEET AUTH
# ===============================
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

sheet = gc.open_by_key("1VNVTYE13BEJ2-P0klp5vI7XdPRd0poZujIyNQuk-nms")
df = pd.DataFrame(sheet.worksheet("Franchise_Summary").get_all_records())

for col in df.columns:
    if df[col].astype(str).str.contains(r'^-?\d+\.\d+,\s*-?\d+\.\d+$').any():
        sp = df[col].astype(str).str.split(",", expand=True)
        df["Latitude"] = pd.to_numeric(sp[0], errors="coerce")
        df["Longitude"] = pd.to_numeric(sp[1], errors="coerce")
        df["Lat_Long"] = df[col]
        break

# ===============================
# RUN
# ===============================
if run:
    ulat, ulng = extract_lat_lng(location_input)
    if ulat is None:
        st.error("❌ Invalid location format")
        st.stop()

    rows = []
    for _, r in df.iterrows():
        if pd.isna(r["Latitude"]) or pd.isna(r["Longitude"]):
            continue
        km = haversine(ulat, ulng, r["Latitude"], r["Longitude"])
        url = f"https://www.google.com/maps/dir/?api=1&origin={ulat},{ulng}&destination={r['Lat_Long']}"
        rows.append({
            "PARTY NAME": r.get("PARTY NAME", ""),
            "ADDRESS": r.get("ADDRESS", ""),
            "KM": round(km, 2),
            "VIEW ROUTE": url
        })

    out = pd.DataFrame(rows).sort_values("KM")

    st.subheader("📊 All Outlet Distances (Nearest → Farthest)")
    st.dataframe(
        out,
        use_container_width=True,
        column_config={
            "VIEW ROUTE": st.column_config.LinkColumn(
                "MAP",
                display_text="View Route"
            )
        }
    )
