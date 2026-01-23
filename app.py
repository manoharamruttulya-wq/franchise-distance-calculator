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
# CSS
# ===============================
st.markdown("""
<style>
.block-container {
    max-width: 1200px;
    padding-top: 1rem;
}

/* HEADER */
.mc-header {
    display: flex;
    align-items: center;
    gap: 14px;
}
.mc-logo img { height: 56px; }
.mc-title { font-size: 30px; font-weight: 900; }
.mc-title .red { color: #b71c1c; }
.mc-sub { font-size: 13px; color: #666; }

/* BUTTON */
.stButton button {
    background-color: #b71c1c;
    color: white;
    font-weight: 700;
    border-radius: 12px;
    height: 52px;
    font-size: 16px;
}
.stButton button:hover { background-color: #8e0000; }

/* TABLE */
.mc-scroll-top, .mc-scroll-bottom {
    overflow-x: auto;
    overflow-y: hidden;
}
.mc-scroll-top { height: 18px; }
.mc-scroll-bottom { max-height: 520px; overflow: auto; }

.mc-table {
    border-collapse: collapse;
    width: 1400px;
    font-size: 14px;
}

.mc-table th {
    background: #b71c1c;
    color: white;
    padding: 8px;
    position: sticky;
    top: 0;
    z-index: 2;
}

.mc-table td {
    padding: 7px;
    border-bottom: 1px solid #eee;
}

.mc-table tr:hover {
    background: #fafafa;
}

@media (max-width: 768px) {
    .mc-header { flex-direction: column; text-align: center; }
}
</style>
""", unsafe_allow_html=True)

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

st.markdown("<br>", unsafe_allow_html=True)

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
    lat1, lon1, lat2, lon2 = map(math.radians,[lat1,lon1,lat2,lon2])
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

# ===============================
# EXTRACT LAT/LONG
# ===============================
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
    sno = 1

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
            "S NO": sno,
            "VIEW ROUTE": route_url,
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

    # ===============================
    # TOP SCROLL BAR
    # ===============================
    st.markdown("""
    <div class="mc-scroll-top" id="top-scroll">
        <div style="width:1400px;height:1px;"></div>
    </div>
    """, unsafe_allow_html=True)

    # ===============================
    # TABLE
    # ===============================
    table_html = """
    <div class="mc-scroll-bottom" id="bottom-scroll">
    <table class="mc-table">
    <thead>
        <tr>
            <th>S No</th>
            <th>View Route</th>
            <th>KM</th>
            <th>Party</th>
            <th>Pincode</th>
            <th>City</th>
            <th>District</th>
            <th>State</th>
            <th>Address</th>
        </tr>
    </thead>
    <tbody>
    """

    for _, r in out.iterrows():
        table_html += f"""
        <tr>
            <td>{r['S NO']}</td>
            <td><a href="{r['VIEW ROUTE']}" target="_blank">View Route</a></td>
            <td>{r['KM']}</td>
            <td>{r['PARTY']}</td>
            <td>{r['PINCODE']}</td>
            <td>{r['CITY']}</td>
            <td>{r['DISTRICT']}</td>
            <td>{r['STATE']}</td>
            <td>{r['ADDRESS']}</td>
        </tr>
        """

    table_html += "</tbody></table></div>"

    st.markdown(table_html, unsafe_allow_html=True)

    # ===============================
    # SCROLL SYNC JS
    # ===============================
    st.markdown("""
    <script>
    const topScroll = document.getElementById("top-scroll");
    const bottomScroll = document.getElementById("bottom-scroll");

    topScroll.onscroll = () => {
        bottomScroll.scrollLeft = topScroll.scrollLeft;
    };
    bottomScroll.onscroll = () => {
        topScroll.scrollLeft = bottomScroll.scrollLeft;
    };
    </script>
    """, unsafe_allow_html=True)
