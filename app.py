import streamlit as st
import math
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===================== UI =====================
st.set_page_config(page_title="Franchise Distance Calculator", layout="wide")
st.title("📍 Franchise Distance Calculator")

st.subheader("Enter New Location")
user_lat = st.number_input("Latitude", format="%.6f")
user_lng = st.number_input("Longitude", format="%.6f")
run = st.button("Calculate Distance")

# ===================== GOOGLE AUTH =====================
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

# ===================== LOAD SHEET =====================
SHEET_ID = "1VNVTYE13BEJ2-P0klp5vI7XdPRd0poZujIyNQuk-nms"
sheet = gc.open_by_key(SHEET_ID)

franchise_df = pd.DataFrame(
    sheet.worksheet("Franchise_Summary").get_all_records()
)

# ===================== LAT/LONG EXTRACT =====================
def extract_lat_lon(df):
    for col in df.columns:
        if df[col].astype(str).str.contains(r'^-?\d+\.\d+,\s*-?\d+\.\d+$').any():
            split = df[col].astype(str).str.split(",", expand=True)
            df["Latitude"] = pd.to_numeric(split[0], errors="coerce")
            df["Longitude"] = pd.to_numeric(split[1], errors="coerce")
            df["Lat_Long"] = df[col]
            break
    return df

franchise_df = extract_lat_lon(franchise_df)

# ===================== HAVERSINE =====================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ===================== MAIN LOGIC =====================
if run:

    if user_lat == 0 or user_lng == 0:
        st.error("Please enter valid Latitude & Longitude")
        st.stop()

    results = []

    for _, fr in franchise_df.iterrows():
        if pd.isna(fr["Latitude"]) or pd.isna(fr["Longitude"]):
            continue

        dist = haversine(
            user_lat, user_lng,
            fr["Latitude"], fr["Longitude"]
        )

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
        })

    # ALL OUTLETS SORTED
    result_df = pd.DataFrame(results).sort_values("KM").reset_index(drop=True)

    # RANK TAG
    def rank_label(i):
        if i == 0: return "1st Nearest"
        if i == 1: return "2nd Nearest"
        if i == 2: return "3rd Nearest"
        if i == 3: return "4th Nearest"
        return ""

    result_df["RANK"] = [rank_label(i) for i in range(len(result_df))]

    # ===================== OUTPUT =====================
    st.subheader("📊 All Outlet Distances (Nearest → Farthest)")
    st.dataframe(
        result_df.drop(columns=["LAT_LONG"]),
        use_container_width=True
    )

    # ===================== 1–4 COMBINED ROUTE =====================
    if len(result_df) >= 4:
        origin = f"{user_lat},{user_lng}"
        destination = result_df.iloc[0]["LAT_LONG"]
        waypoints = "|".join(
            result_df.iloc[1:4]["LAT_LONG"].tolist()
        )

        combined_map = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}"
            f"&destination={destination}"
            f"&waypoints={waypoints}"
            "&travelmode=walking"
        )

        st.subheader("🗺️ 1–4 Combined Route")
        st.markdown(f"[View 1st–4th Combined Route]({combined_map})")

    # ===================== CSV DOWNLOAD =====================
    csv = result_df.drop(columns=["LAT_LONG"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Full Distance Report",
        csv,
        "all_outlet_distance_report.csv",
        "text/csv"
    )
