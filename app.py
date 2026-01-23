import streamlit as st
import pandas as pd
import math
import re
import requests

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Manohar Chai | Franchise Distance Tool",
    layout="wide"
)

# ===============================
# BASIC UI / BRANDING
# ===============================
st.markdown("""
<style>
.header {
    display:flex;
    align-items:center;
    gap:16px;
    margin-top:40px;
    margin-bottom:30px;
}
.header img { height:70px; }
.brand {
    font-size:34px;
    font-weight:800;
}
.brand span { color:#c01818; }
.subtitle {
    color:#666;
    margin-top:-6px;
}

.card {
    background:white;
    padding:24px;
    border-radius:18px;
    box-shadow:0 8px 20px rgba(0,0,0,0.08);
    margin-bottom:30px;
}

.stButton > button {
    background:#c01818;
    color:white;
    font-size:18px;
    padding:14px;
    border-radius:14px;
    width:100%;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
    <img src="ManoharLogo_Social.png">
    <div>
        <div class="brand"><span>MANOHAR</span> CHAI</div>
        <div class="subtitle">Franchise Distance Calculator · Internal Office Use Only</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===============================
# HELPERS
# ===============================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians,[lat1,lon1,lat2,lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def extract_latlon(text):
    m = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None

def expand_short_url(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.url
    except:
        return url

def get_latlon(input_text):
    if not input_text:
        return None

    # direct lat,long
    ll = extract_latlon(input_text)
    if ll:
        return ll

    # maps.app.goo.gl support
    if "maps.app.goo.gl" in input_text:
        input_text = expand_short_url(input_text)

    return extract_latlon(input_text)

# ===============================
# SAMPLE DATA (replace with Google Sheet later)
# ===============================
outlets = pd.DataFrame([
    {
        "PARTY NAME":"Outlet A",
        "PINCODE":"480001",
        "CITY":"Chhindwara",
        "DISTRICT":"Chhindwara",
        "STATE":"Madhya Pradesh",
        "ADDRESS":"Main Road",
        "LAT":22.0532,
        "LON":78.9435
    },
    {
        "PARTY NAME":"Outlet B",
        "PINCODE":"480002",
        "CITY":"Chhindwara",
        "DISTRICT":"Chhindwara",
        "STATE":"Madhya Pradesh",
        "ADDRESS":"Bus Stand",
        "LAT":22.0496,
        "LON":78.9389
    },
    {
        "PARTY NAME":"Outlet C",
        "PINCODE":"480003",
        "CITY":"Chhindwara",
        "DISTRICT":"Chhindwara",
        "STATE":"Madhya Pradesh",
        "ADDRESS":"Nagpur Road",
        "LAT":22.0603,
        "LON":78.9521
    }
])

# ===============================
# INPUT
# ===============================
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown("📍 **Enter Location**")
location_input = st.text_input(
    "Paste Lat,Long OR Google Maps link",
    placeholder="22.05762,78.93807  OR  https://maps.app.goo.gl/..."
)

calculate = st.button("🔍 Calculate Distance")

st.markdown('</div>', unsafe_allow_html=True)

# ===============================
# RESULT
# ===============================
if calculate:
    latlon = get_latlon(location_input)

    if not latlon:
        st.error("❌ Invalid location format. Please paste Google Maps link or lat,long.")
    else:
        lat, lon = latlon
        rows = []

        for _, r in outlets.iterrows():
            km = haversine(lat, lon, r["LAT"], r["LON"])
            route = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={lat},{lon}"
                f"&destination={r['LAT']},{r['LON']}"
            )

            rows.append({
                "View Route": f"[View Route]({route})",   # 1
                "KM": round(km, 2),                       # 2
                "Party": r["PARTY NAME"],                 # 3
                "Pincode": r["PINCODE"],                  # 4
                "City": r["CITY"],                        # 5
                "District": r["DISTRICT"],                # 6
                "State": r["STATE"],                      # 7
                "Address": r["ADDRESS"]                   # 8
            })

        result_df = pd.DataFrame(rows).sort_values("KM")

        st.markdown("### 📊 All Outlet Distances (Nearest → Farthest)")
        st.markdown(result_df.to_markdown(index=False), unsafe_allow_html=True)
