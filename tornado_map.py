# tornado_map.py
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "folium", "branca"]
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

required_columns = {"year", "lat", "lon"}
missing_columns = required_columns - set(df.columns)
if missing_columns:
    missing = ", ".join(sorted(missing_columns))
    raise ValueError(f"Missing required tornado data columns: {missing}")

df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.loc[df["year"].between(1950, 2021)].copy()

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
if "f_scale" not in df.columns:
    df["f_scale"] = 0
else:
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
    if col not in df.columns:
        df[col] = 0
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
    <div style="font-family: Arial, sans-serif; width: 100%; line-height: 2.2; font-size: 16px; box-sizing: border-box;">
        <div style="padding-bottom: 12px; font-size: 22px; line-height: 1.3; text-align: center;">
            <b>{state}</b>
        </div>
        <div style="width: calc(100% - 24px); height: 5px; margin: 0 auto 6px; border-radius: 999px; background: #9aa4ad;"></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Year</b><span>{year}</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Latitude</b><span>{lat:.2f}</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Longitude</b><span>{lon:.2f}</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Fatalities</b><span>{deaths}</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Injuries</b><span>{injuries}</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>F/EF Scale</b><span>{scale}</span></div>
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
    tiles=None,
    min_zoom=5,
    min_lat=24,
    max_lat=50,
    min_lon=-125,
    max_lon=-66.5,
    max_bounds=True,
)

folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
    attr="&copy; OpenStreetMap contributors &copy; CARTO",
    name="Simple light map",
    subdomains="abcd",
    max_zoom=20,
).add_to(m)

# ------------------------------------------------------------
# 7) Prepare compact marker data for the browser
# ------------------------------------------------------------
tornado_records = []
for _, row in df.iterrows():
    state_code = str(row.get("state", "Unknown"))
    tornado_records.append([
        int(row["year"]),
        escape(STATE_NAMES.get(state_code, state_code)),
        float(row["lat"]),
        float(row["lon"]),
        int(row["fatalities"]),
        int(row["injuries"]),
        int(row["f_scale"]),
        scale_color(int(row["f_scale"])),
    ])

# Add a small, dependency-free range control to the generated Leaflet page.
min_year = int(df["year"].min())
max_year = int(df["year"].max())
records_json = json.dumps(tornado_records, separators=(",", ":"))
slider = f"""
<style>
    #year-slider {{
        width: 100%;
        height: 18px;
        accent-color: #2563eb;
        cursor: pointer;
    }}
    #year-slider::-webkit-slider-runnable-track {{
        height: 8px;
        border-radius: 999px;
        background: #d6dbe1;
    }}
    #year-slider::-webkit-slider-thumb {{
        appearance: none;
        width: 18px;
        height: 18px;
        margin-top: -5px;
        border: 2px solid #ffffff;
        border-radius: 50%;
        background: #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,.3);
    }}
    #year-slider::-moz-range-track {{
        height: 8px;
        border-radius: 999px;
        background: #d6dbe1;
    }}
    #year-slider::-moz-range-thumb {{
        width: 18px;
        height: 18px;
        border: 2px solid #ffffff;
        border-radius: 50%;
        background: #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,.3);
    }}
</style>
<div id="map-controls" style="
    position: fixed; z-index: 9999; top: 0; right: 0; bottom: 0;
    width: min(320px, 100vw); display: flex; flex-direction: column;
    overflow-y: auto; background: #ffffff; box-shadow: -2px 0 10px rgba(0,0,0,.18);
">
<div id="tornado-details" style="
    display: block; width: 100%; box-sizing: border-box; padding: 14px 16px;
    border: 0; border-bottom: 1px solid #c7cdd4;
    background: #ffffff; font: 16px Arial, sans-serif; line-height: 2.2;
    color: #263238; overflow-y: auto; flex: 1; min-height: 0;
">
    <div id="tornado-details-content">
        <div style="padding-bottom: 6px; text-align: center;">
            <b style="font-size: 22px;">Selected tornado</b>
        </div>
        <div style="width: calc(100% - 24px); height: 5px; margin: 0 auto 6px; border-radius: 999px; background: #9aa4ad;"></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>State</b><span>N/A</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Year</b><span>N/A</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Latitude</b><span>N/A</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Longitude</b><span>N/A</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Fatalities</b><span>0</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Injuries</b><span>0</span></div>
        <div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>F/EF Scale</b><span>N/A</span></div>
    </div>
</div>
<div id="year-range-control" style="
    width: 100%; box-sizing: border-box; padding: 14px 16px; margin-top: auto;
    border: 0; border-top: 1px solid #c7cdd4;
    background: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,.18);
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
</div>
<script>
window.addEventListener('load', function() {{
    var map = {m.get_name()};
    var tornadoRecords = {records_json};
    var slider = document.getElementById('year-slider');
    var label = document.getElementById('year-label');
    var detailsContent = document.getElementById('tornado-details-content');
    var activeLayer = null;

    function makeDetailsHtml(record) {{
        return '<div style="font-family: Arial, sans-serif; width: 100%; line-height: 2.2; font-size: 16px; box-sizing: border-box;">' +
            '<div style="padding-bottom: 12px; font-size: 22px; line-height: 1.3; text-align: center;"><b>' + record[1] + '</b></div>' +
            '<div style="width: calc(100% - 24px); height: 5px; margin: 0 auto 6px; border-radius: 999px; background: #9aa4ad;"></div>' +
            '<div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Year</b><span>' + record[0] + '</span></div>' +
            '<div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Latitude</b><span>' + record[2].toFixed(2) + '</span></div>' +
            '<div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Longitude</b><span>' + record[3].toFixed(2) + '</span></div>' +
            '<div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Fatalities</b><span>' + record[4] + '</span></div>' +
            '<div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>Injuries</b><span>' + record[5] + '</span></div>' +
            '<div style="display: flex; justify-content: space-between; padding-bottom: 10px;"><b>F/EF Scale</b><span>' + record[6] + '</span></div>' +
            '</div>';
    }}

    function updateYear() {{
        var selectedYear = Number(slider.value);
        label.textContent = selectedYear;
        if (activeLayer) map.removeLayer(activeLayer);
        activeLayer = L.featureGroup();
        tornadoRecords.forEach(function(record) {{
            if (record[0] !== selectedYear) return;
            var radius = Math.max(4, Math.min(18, 4 + record[4] * 2 + record[5] * 0.25));
            var marker = L.circleMarker([record[2], record[3]], {{
                radius: radius, color: record[7], weight: 1,
                fill: true, fillColor: record[7], fillOpacity: 0.75
            }});
            marker.bindTooltip(record[1] + ' • ' + record[0] + ' • F/EF ' + record[6]);
            marker.on('click', function() {{
                detailsContent.innerHTML = makeDetailsHtml(record);
            }});
            marker.addTo(activeLayer);
        }});
        activeLayer.addTo(map);
    }}

    slider.addEventListener('input', updateYear);
    updateYear();
}});
</script>
"""
m.get_root().html.add_child(Element(slider))

# ------------------------------------------------------------
# 8) Save the map
# ------------------------------------------------------------
out_dir = root / "out"
out_dir.mkdir(exist_ok=True)
output_path = out_dir / "tornado_map.html"
m.save(output_path)

print(f"Saved map to: {output_path.resolve()}")