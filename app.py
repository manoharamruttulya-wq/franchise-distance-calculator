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
# LOAD GOOGLE API KEY SAFELY
# ===============================
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")

# ===============================
# SMART GEOCODE (CACHED)
# ===============================
@st.cache_data(show_spinner=False)
def geocode_address(address, api_key):
    if not api_key:
        return None, None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except:
        pass

    return None, None


# ===============================
# HYBRID COORD EXTRACT
# ===============================
def extract_lat_lng(text):
    if not text:
        return None, None

    text = text.strip()

    # 1️⃣ Direct lat,long
    match = re.search(r'^(-?\d+\.\d+),\s*(-?\d+\.\d+)$', text)
    if match:
        return float(match.group(1)), float(match.group(2))

    # 2️⃣ Extract from Google URL
    patterns = [
        r'@(-?\d+\.\d+),(-?\d+\.\d+)',
        r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            return float(m.group(1)), float(m.group(2))

    # 3️⃣ Fallback to API
    return geocode_address(text, GOOGLE_API_KEY)


# ===============================
# DISTANCE FUNCTION
# ===============================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians,[lat1,lon1,lat2,lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# ===============================
# UI
# ===============================
st.title("☕ MANOHAR CHAI – Franchise Distance Tool")

location_input = st.text_input(
    "Paste Lat,Long OR Google Maps link OR Address"
)

run = st.button("🔍 Calculate Distance", use_container_width=True)


# ===============================
# GOOGLE SHEET CONNECTION
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

# Extract Lat/Long from sheet
for col in df.columns:
    if df[col].astype(str).str.contains(r'^-?\d+\.\d+,\s*-?\d+\.\d+$').any():
        split = df[col].astype(str).str.split(",", expand=True)
        df["Latitude"] = pd.to_numeric(split[0], errors="coerce")
        df["Longitude"] = pd.to_numeric(split[1], errors="coerce")
        break


# ===============================
# RUN
# ===============================
if run:

    ulat, ulng = extract_lat_lng(location_input)

    if ulat is None:
        st.error("❌ Could not extract coordinates.")
        st.stop()

    rows = []

    for _, r in df.iterrows():

        if pd.isna(r.get("Latitude")) or pd.isna(r.get("Longitude")):
            continue

        km = haversine(ulat, ulng, r["Latitude"], r["Longitude"])

        route_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={ulat},{ulng}"
            f"&destination={r['Latitude']},{r['Longitude']}"
        )

        rows.append({
            "VIEW ROUTE": route_url,
            "KM": round(km, 2),
            "PARTY": r.get("PARTY NAME", ""),
            "CITY": r.get("CITY", ""),
            "STATE": r.get("STATE", "")
        })

    if not rows:
        st.warning("No valid outlet coordinates found.")
        st.stop()

    out = pd.DataFrame(rows).sort_values("KM")

    st.subheader("📊 All Outlet Distances (Nearest → Farthest)")

    st.dataframe(
        out,
        use_container_width=True,
        column_config={
            "VIEW ROUTE": st.column_config.LinkColumn(
                "View Route",
                display_text="View Route"
            )
        }
    )
