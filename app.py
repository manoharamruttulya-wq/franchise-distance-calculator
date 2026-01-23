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

        route_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={ulat},{ulng}"
            f"&destination={r['Lat_Long']}"
        )

        rows.append({
            "VIEW ROUTE": route_url,                      # 1️⃣
            "KM": round(km, 2),                           # 2️⃣
            "PARTY": r.get("PARTY NAME", ""),             # 3️⃣
            "PINCODE": r.get("PINCODE", ""),              # 4️⃣
            "CITY": r.get("CITY", ""),                    # 5️⃣
            "DISTRICT": r.get("DISTRICT", ""),            # 6️⃣
            "STATE": r.get("STATE", ""),                  # 7️⃣
            "ADDRESS": r.get("ADDRESS", "")               # 8️⃣
        })

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
