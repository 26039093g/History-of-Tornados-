# tornado_map.py
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "folium"]
# ///

import pandas as pd
import folium
import json
from branca.element import Element
from pathlib import Path
from html import escape

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia", "PR": "Puerto Rico",
}

# ------------------------------------------------------------
# 1) Load the tornado dataset
# ------------------------------------------------------------
# The repository stores the source data as us_tornado_dataset_1950_2021.csv,
# so we resolve that file automatically and also support the common
# data/tornadoes.csv location used by the assignment template.
# ------------------------------------------------------------
root = Path(__file__).resolve().parent
csv_path = root / "data" / "tornadoes.csv"
source_csv = root / "us_tornado_dataset_1950_2021.csv"

if not csv_path.exists() and source_csv.exists():
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_bytes(source_csv.read_bytes())

if not csv_path.exists():
    raise FileNotFoundError(
        "Could not find tornado data. Expected one of: "
        f"{csv_path} or {source_csv}"
    )

df = pd.read_csv(csv_path)

# Keep only the data range we want.
df.columns = [str(c).strip().lower() for c in df.columns]

authorized_years = (df["yr"] >= 1950) & (df["yr"] <= 2021)
df = df.loc[authorized_years].copy()

# ------------------------------------------------------------
# 2) Normalize column names
# ------------------------------------------------------------
# This dataset uses start latitude/longitude columns, not the generic names in
# the template, so we map the real names to the expected ones used below.
rename_map = {
    "yr": "year",
    "dy": "day",
    "mo": "month",
    "st": "state",
    "slat": "lat",
    "slon": "lon",
    "mag": "f_scale",
    "inj": "injuries",
    "fat": "fatalities",
    "state_name": "state",
    "latitude": "lat",
    "longitude": "lon",
    "f_scale": "f_scale",
    "ef_scale": "f_scale",
    "magnitude": "f_scale",
    "fujita": "f_scale",
}
for old, new in rename_map.items():
    if old in df.columns and new not in df.columns:
        df = df.rename(columns={old: new})

# If both start and end coordinates exist, prefer start coordinates to keep the
# point map consistent with a single tornado touchdown location.
if "lat" not in df.columns and "slat" in df.columns:
    df = df.rename(columns={"slat": "lat", "slon": "lon"})

# ------------------------------------------------------------
# 3) Clean the data
# ------------------------------------------------------------
for col in ["year", "lat", "lon", "fatalities", "injuries"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Keep only valid locations
df = df.dropna(subset=["lat", "lon"]).copy()

# Standardize scale values
if "f_scale" in df.columns:
    df["f_scale"] = df["f_scale"].astype(str).str.strip().str.upper()
    df["f_scale"] = df["f_scale"].replace({
        "F0": "0", "F1": "1", "F2": "2", "F3": "3", "F4": "4", "F5": "5",
        "EF0": "0", "EF1": "1", "EF2": "2", "EF3": "3", "EF4": "4", "EF5": "5",
        "0.0": "0", "1.0": "1", "2.0": "2", "3.0": "3", "4.0": "4", "5.0": "5",
        "-9": "0", "-9.0": "0",
    })
    df["f_scale"] = pd.to_numeric(df["f_scale"], errors="coerce")

# Fill missing scale values with 0 so the map still works
df["f_scale"] = df["f_scale"].fillna(0)

# Fill missing fatality/injury counts with 0
for col in ["fatalities", "injuries"]:
    if col in df.columns:
        df[col] = df[col].fillna(0)

# State codes are typically abbreviations; keep them uppercase for display.
if "state" in df.columns:
    df["state"] = df["state"].astype(str).str.strip().str.upper().replace({"nan": "Unknown"})

# ------------------------------------------------------------
# 4) Helper function for popup content
# ------------------------------------------------------------
def make_popup_html(row):
    state_code = str(row.get("state", "Unknown"))
    state = escape(STATE_NAMES.get(state_code, state_code))
    year = int(row.get("year", 0))
    lat = row.get("lat", 0)
    lon = row.get("lon", 0)
    deaths = int(row.get("fatalities", 0))
    injuries = int(row.get("injuries", 0))
    scale = int(row.get("f_scale", 0))

    html = f"""
    <div style="font-family: Arial, sans-serif; width: 240px; line-height: 1.6; box-sizing: border-box;">
        <div style="width: calc(100% - 24px); box-sizing: border-box; padding-bottom: 6px; margin-bottom: 6px; border-bottom: 5px solid #9aa4ad;">
            <b>{state}</b>
        </div>
        <b>Year:</b> {year}<br>
        <b>Latitude:</b> {lat:.2f}<br>
        <b>Longitude:</b> {lon:.2f}<br>
        <b>Fatalities:</b> {deaths}<br>
        <b>Injuries:</b> {injuries}<br>
        <b>F/EF Scale:</b> {scale}<br>
    </div>
    """
    return html

# ------------------------------------------------------------
# 5) Map styling by tornado scale
# ------------------------------------------------------------
def scale_color(scale):
    if scale >= 5:
        return "#7f0000"   # dark red
    elif scale >= 4:
        return "#d7301f"
    elif scale >= 3:
        return "#f46d43"
    elif scale >= 2:
        return "#fdae61"
    elif scale >= 1:
        return "#fee08b"
    else:
        return "#1a9850"  # weak or unknown

# ------------------------------------------------------------
# 6) Create the US map
# ------------------------------------------------------------
center_lat = 39.5
center_lon = -98.35

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=5,
    tiles="OpenStreetMap",
    min_zoom=5,
    min_lat=24,
    max_lat=50,
    min_lon=-125,
    max_lon=-66.5,
    max_bounds=True,
)

# Use one feature layer per year so the browser can show only the selected year.
year_clusters = {}
marker_details = []
for year in sorted(df["year"].dropna().astype(int).unique()):
    year_clusters[year] = folium.FeatureGroup(name=str(year), show=False).add_to(m)

# ------------------------------------------------------------
# 7) Add one marker per tornado record
# ------------------------------------------------------------
for _, row in df.iterrows():
    popup_html = make_popup_html(row)
    radius = 4 + row["fatalities"] * 2 + row["injuries"] * 0.25
    radius = max(radius, 4)
    radius = min(radius, 18)

    marker = folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=radius,
        color=scale_color(int(row["f_scale"])),
        weight=1,
        fill=True,
        fill_color=scale_color(int(row["f_scale"])),
        fill_opacity=0.75,
        tooltip=f"{STATE_NAMES.get(str(row.get('state', 'Unknown')), row.get('state', 'Unknown'))} • {int(row.get('year', 0))} • F/EF {int(row.get('f_scale', 0))}"
    )
    marker.add_to(year_clusters[int(row["year"])])
    marker_details.append((marker.get_name(), popup_html))

# Add a small, dependency-free range control to the generated Leaflet page.
min_year = int(df["year"].min())
max_year = int(df["year"].max())
cluster_names = ",\n        ".join(
    f"{year}: {cluster.get_name()}" for year, cluster in year_clusters.items()
)
slider = f"""
<div id="tornado-details" style="
    display: none; position: fixed; z-index: 9999; top: 20px; right: 20px;
    width: 240px; padding: 14px 36px 14px 16px; border: 1px solid #c7cdd4;
    border-radius: 8px; background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 2px 10px rgba(0,0,0,.18); font: 14px Arial, sans-serif;
    color: #263238;
">
    <button id="close-tornado-details" type="button" aria-label="Close tornado details" style="
        position: absolute; top: 8px; right: 8px; border: 0; background: transparent;
        font-size: 20px; line-height: 1; cursor: pointer; color: #59636e;
    ">&times;</button>
    <div id="tornado-details-content"></div>
</div>
<div id="year-range-control" style="
    position: fixed; z-index: 9999; left: 50%; bottom: 24px;
    transform: translateX(-50%); width: min(420px, calc(100vw - 40px));
    padding: 14px 16px; border: 1px solid #c7cdd4; border-radius: 8px;
    background: rgba(255, 255, 255, 0.96); box-shadow: 0 2px 10px rgba(0,0,0,.18);
    font: 14px Arial, sans-serif; color: #263238;
">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <strong>Tornado year</strong>
        <span id="year-label">{min_year}</span>
    </div>
    <div style="display:grid; gap:6px;">
        <label for="year-slider">Select a year</label>
        <input id="year-slider" type="range" min="{min_year}" max="{max_year}" value="{min_year}" step="1" aria-label="Select a year">
    </div>
</div>
<script>
window.addEventListener('load', function() {{
    var map = {m.get_name()};
    var clusters = {{
        {cluster_names}
    }};
    var slider = document.getElementById('year-slider');
    var label = document.getElementById('year-label');
    var details = document.getElementById('tornado-details');
    var detailsContent = document.getElementById('tornado-details-content');
    var markerDetails = [
        {",\n        ".join(f"[{marker}, {json.dumps(html)}]" for marker, html in marker_details)}
    ];

    function updateYear() {{
        var selectedYear = Number(slider.value);
        label.textContent = selectedYear;
        Object.keys(clusters).forEach(function(year) {{
            var cluster = clusters[year];
            var visible = Number(year) === selectedYear;
            if (visible && !map.hasLayer(cluster)) map.addLayer(cluster);
            if (!visible && map.hasLayer(cluster)) map.removeLayer(cluster);
        }});
    }}

    slider.addEventListener('input', updateYear);
    markerDetails.forEach(function(item) {{
        item[0].on('click', function() {{
            detailsContent.innerHTML = item[1];
            details.style.display = 'block';
        }});
    }});
    document.getElementById('close-tornado-details').addEventListener('click', function() {{
        details.style.display = 'none';
    }});
    updateYear();
}});
</script>
"""
m.get_root().html.add_child(Element(slider))

# ------------------------------------------------------------
# 8) Save the map
# ------------------------------------------------------------
out_dir = Path("out")
out_dir.mkdir(exist_ok=True)
output_path = out_dir / "tornado_map.html"
m.save(output_path)

print(f"Saved map to: {output_path.resolve()}")