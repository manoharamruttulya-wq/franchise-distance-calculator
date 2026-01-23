import streamlit as st
import math
import pandas as pd
import gspread
import re
import requests
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="Manohar Chai – Franchise Distance Tool",
    layout="wide"
)

# =============================
# CSS
# =============================
st.markdown("""
<style>
.block-container {
    max-width: 1400px;
    padding-top: 20px;
}

/* HEADER */
.mc-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 40px;
}
.mc-logo img {
    height: 60px;
}
.mc-title {
    font-size: 32px;
    font-weight: 900;
}
.mc-title .red { color: #b71c1c; }
.mc-sub {
    font-size: 13px;
    color: #666;
}

/* BUTTON */
.stButton button {
    background-color: #b71c1c;
    color: white;
    font-weight: 700;
    border-radius: 12px;
    height: 54px;
    font-size: 16px;
}
.stButton button:hover {
    background-color: #8e0000;
}

/* TABLE */
.table-wrapper {
    width: 100%;
    overflow-x: auto;
    border: 1px solid #ddd;
    border-radius: 12px;
}

.custom-table {
    border-collapse: collapse;
    min-width: 1600px;
    width: 100%;
    font-size: 14px;
}

.custom-table thead th {
    background: #b71c1c;
    color: #ffffff;
    padding: 10px;
    text-align: left;
    white-space: nowrap;
}

.custom-table tbody td {
    padding: 8px 10px;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
}

.custom-table tbody tr:hover {
    background: #fff3f3;
}

.route-link {
    color: #1565c0;
    font-weight: 600;
    text-decoration: none;
}
.route-link:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

# =============================
# HEADER
# =============================
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

st.markdown("<br><br>", unsafe_allow_html=True)

# =============================
# INPUT
# =============================
st.subheader("📍 Enter Location")

location_input = st.text_input(
    "Paste Lat,Long OR Google Maps link",
    placeholder="22.05762,78.93807  OR  https://maps.app.goo.gl/xxxx"
)

run = st.button("🔍 Calculate Distance", use_container_width=True)

# =============================
# HELPERS
# =============================
def extract_lat_lng(text):
    if not text:
        return None, None

    if "maps.app.goo.gl" in text:
        try:
            r = requests.get(text, allow_redirects=True, timeout=10)
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

# =============================
# GOOGLE SHEET
# =============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    dict(st.secrets["gcp"]),
    scope
)

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

# =============================
# RUN
# =============================
if run:
    ulat, ulng = extract_lat_lng(location_input)
    if ulat is None:
        st.error("❌ Invalid location format")
        st.stop()

    rows = []
    sno = 1

    for _, r in df.iterrows():
        if pd.isna(r.get("Latitude")) or pd.isna(r.get("Longitude")):
            continue

        km = haversine(ulat, ulng, r["Latitude"], r["Longitude"])
        route = f"https://www.google.com/maps/dir/?api=1&origin={ulat},{ulng}&destination={r['Lat_Long']}"

        rows.append({
            "SNO": sno,
            "ROUTE": route,
            "KM": round(km, 2),
            "PARTY": r.get("PARTY NAME", ""),
            "PINCODE": r.get("PINCODE", ""),
            "CITY": r.get("CITY", ""),
            "DISTRICT": r.get("DISTRICT", ""),
            "STATE": r.get("STATE", ""),
            "ADDRESS": r.get("ADDRESS", "")
        })
        sno += 1

    out = pd.DataFrame(rows).sort_values("KM")

    # =============================
    # HTML TABLE (FINAL)
    # =============================
    html = """
    <div class="table-wrapper">
    <table class="custom-table">
        <thead>
            <tr>
                <th>S NO</th>
                <th>VIEW ROUTE</th>
                <th>KM</th>
                <th>PARTY</th>
                <th>PINCODE</th>
                <th>CITY</th>
                <th>DISTRICT</th>
                <th>STATE</th>
                <th>ADDRESS</th>
            </tr>
        </thead>
        <tbody>
    """

    for _, r in out.iterrows():
        html += f"""
        <tr>
            <td>{r['SNO']}</td>
            <td><a class="route-link" href="{r['ROUTE']}" target="_blank">View Route</a></td>
            <td>{r['KM']}</td>
            <td>{r['PARTY']}</td>
            <td>{r['PINCODE']}</td>
            <td>{r['CITY']}</td>
            <td>{r['DISTRICT']}</td>
            <td>{r['STATE']}</td>
            <td>{r['ADDRESS']}</td>
        </tr>
        """

    html += "</tbody></table></div>"

    st.subheader("📊 All Outlet Distances (Nearest → Farthest)")
    components.html(html, height=600, scrolling=True)
