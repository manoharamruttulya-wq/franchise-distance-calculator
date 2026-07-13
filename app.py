import streamlit as st
import math
import pandas as pd
import gspread
import re
import requests
from google.oauth2.service_account import Credentials

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Manohar Chai – Franchise Distance Tool",
    layout="wide"
)

# ===============================
# CSS (Purana Wala - Same)
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
# HEADER (Purana Wala - Same)
# ===============================
st.markdown("<div style='height:76px'></div>", unsafe_allow_html=True)

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
# INPUT (Purana Wala - Same)
# ===============================
st.subheader("📍 Enter Location")

location_input = st.text_input(
    "Paste Lat,Long OR Google Maps link",
    placeholder="22.05762,78.93807  OR  https://maps.app.goo.gl/..."
)

run = st.button("🔍 Calculate Distance", use_container_width=True)

# ===============================
# HELPERS (Purana Wala - Same)
# ===============================
def extract_lat_lng(text):
    if not text:
        return None, None
    if "maps.app.goo.gl" in text or "goo.gl" in text:
        try:
            r = requests.get(text, allow_redirects=True, timeout=5)
            text = r.url
        except:
            return None, None
    patterns = [
        r'(-?\d+\.\d+),\s*(-?\d+\.\d+)',
        r'@(-?\d+\.\d+),(-?\d+\.\d+)',
        r'[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)',
        r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'
    ]
    for p in patterns:
        m = re.search(p, text)
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
# GOOGLE SHEET - CACHED
# ===============================
@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
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
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Google Auth Error: {e}")
        return None

@st.cache_data(ttl=1800)
def get_franchise_data():
    try:
        gc = get_gspread_client()
        if gc is None:
            return None
        sheet = gc.open_by_key("1VNVTYE13BEJ2-P0klp5vI7XdPRd0poZujIyNQuk-nms")
        df = pd.DataFrame(sheet.worksheet("Franchise_Summary").get_all_records())
        for col in df.columns:
            if df[col].astype(str).str.contains(r'^-?\d+\.\d+,\s*-?\d+\.\d+$').any():
                split = df[col].astype(str).str.split(",", expand=True)
                df["Latitude"] = pd.to_numeric(split[0], errors="coerce")
                df["Longitude"] = pd.to_numeric(split[1], errors="coerce")
                df["Lat_Long"] = df[col]
                break
        return df
    except Exception as e:
        st.error(f"❌ Sheet Error: {e}")
        return None

# ===============================
# RUN
# ===============================
if run:
    with st.spinner("📊 Loading franchise data..."):
        df = get_franchise_data()
    
    if df is None:
        st.stop()

    ulat, ulng = extract_lat_lng(location_input)
    if ulat is None:
        st.error("❌ Invalid location format")
        st.stop()

    rows = []
    for _, r in df.iterrows():
        if pd.isna(r["Latitude"]) or pd.isna(r["Longitude"]):
            continue
        km = haversine(ulat, ulng, r["Latitude"], r["Longitude"])
        route_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={ulat},{ulng}"
            f"&destination={r['Lat_Long']}"
        )
        rows.append({
            "VIEW ROUTE": route_url,
            "KM": round(km, 2),
            "PARTY": str(r.get("PARTY NAME", "")),
            "PINCODE": str(r.get("PINCODE", "")),
            "CITY": str(r.get("CITY", "")),
            "DISTRICT": str(r.get("DISTRICT", "")),
            "STATE": str(r.get("STATE", "")),
            "ADDRESS": str(r.get("ADDRESS", ""))
        })

    out = pd.DataFrame(rows).sort_values("KM")

    st.subheader("📊 All Outlet Distances (Nearest → Farthest)")
    
    # Yahan purana table format wapas laya hai
    st.dataframe(
        out,
        use_container_width=True,
        height=450,  # Table ki height fix kar di (10 rows ke liye perfect)
        column_config={
            "VIEW ROUTE": st.column_config.LinkColumn(
                "🗺️ View Route",  # Sirf ye text dikhega, URL nahi dikhega
                display_text="View Route"
            )
        }
    )
