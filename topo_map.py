import folium
from pyproj import Transformer
import requests
import webbrowser, os
from folium import FeatureGroup
from collections import defaultdict

# --- UTM Zone 51N Coordinates ---
utm_points = [
    (486261.21, 1087959.88),
    (485907.87, 1088478.4),
    (485577.86, 1088967.78),
    (485811.46, 1089136.73),
    (486337.73, 1089587.77),
    (486517.81, 1089204.63),
    (486769.58, 1088814.35),
    (486673.53, 1088554.66),
    (486693.62, 1088236.22),
    (486640.04, 1088143.97),
    (486505.48, 1087996.02),
    (486402.61, 1087930.75),
    (486390.62, 1087993.53),
    (486261.21, 1087959.88)
]

# --- Convert UTM to Lat/Lon ---
transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
latlon_points = [transformer.transform(x, y) for x, y in utm_points]

# --- Fetch Elevation via Open-Elevation API ---
def get_elevation(lat, lon):
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()["results"][0]["elevation"]
    except:
        return None
    return None

# --- DMS Conversion ---
def decimal_to_dms(deg):
    d = int(deg)
    m_float = abs(deg - d) * 60
    m = int(m_float)
    s = (m_float - m) * 60
    return d, m, s

def format_dms(deg, is_lat=True):
    d, m, s = decimal_to_dms(deg)
    direction = 'N' if is_lat and deg >= 0 else 'S' if is_lat else 'E' if deg >= 0 else 'W'
    return f"{abs(d)}°{m}'{s:.1f}\"{direction}"

# --- Get Elevations ---
elevations = []
for lon, lat in latlon_points:
    z = get_elevation(lat, lon)
    elevations.append(z)

# --- Group Points by Similar Elevation (rounded to nearest 5 meters) ---
elevation_groups = defaultdict(list)
for (lon, lat), z in zip(latlon_points, elevations):
    if z is not None:
        rounded = round(z / 5) * 5
        elevation_groups[rounded].append((lat, lon))

# --- Setup Map ---
center_lat = sum(lat for _, lat in latlon_points) / len(latlon_points)
center_lon = sum(lon for lon, _ in latlon_points) / len(latlon_points)
m = folium.Map(location=[center_lat, center_lon], zoom_start=18, control_scale=True)

# --- Draw Main Centerline ---
folium.PolyLine([(lat, lon) for lon, lat in latlon_points], color='blue', weight=4).add_to(m)

# --- Draw Green Elevation Lines ---
for elev, group in elevation_groups.items():
    if len(group) >= 2:
        folium.PolyLine(group, color='green', weight=2.5, tooltip=f"Contour ~{elev} m").add_to(m)

# --- Sidebar with Coordinates and Elevations ---
sidebar_html = """
<div style="position: fixed; top: 20px; left: 70px; width: 200px; background: white;
    padding: 10px; border: 1px solid black; border-radius: 5px; font-family: Arial;
    font-size: 12px; z-index: 9999; max-height: 90vh; overflow-y: auto;" id="sidebar">
    <label><b>Coordinate View</b></label>
    <select onchange="toggleFormat(this.value)" style="margin-bottom: 10px; width: 100%;">
        <option value="dms">DMS</option>
        <option value="utm">UTM (E/N)</option>
        <option value="ne">N/E</option>
    </select>
    <div id="coord-list">
"""

for i, ((lon, lat), (x, y), z) in enumerate(zip(latlon_points, utm_points, elevations)):
    lat_dms = format_dms(lat, is_lat=True)
    lon_dms = format_dms(lon, is_lat=False)
    z_disp = f"{z} m" if z is not None else "N/A"
    sidebar_html += f"""
    <div>
        <b>Point {i+1}</b><br>
        <span class="coord-dms">{lat_dms}<br>{lon_dms}<br>Elevation: {z_disp}</span>
        <span class="coord-utm" style="display:none;">E: {x:.2f}<br>N: {y:.2f}<br>Elevation: {z_disp}</span>
        <span class="coord-ne" style="display:none;">N: {y:.2f}<br>E: {x:.2f}<br>Elevation: {z_disp}</span>
    </div>
    <hr style="margin:4px 0;">
    """

sidebar_html += """
    </div>
</div>
<script>
function toggleFormat(fmt) {
    document.querySelectorAll('.coord-dms').forEach(el => el.style.display = fmt === 'dms' ? 'block' : 'none');
    document.querySelectorAll('.coord-utm').forEach(el => el.style.display = fmt === 'utm' ? 'block' : 'none');
    document.querySelectorAll('.coord-ne').forEach(el => el.style.display = fmt === 'ne' ? 'block' : 'none');
}
</script>
"""
m.get_root().html.add_child(folium.Element(sidebar_html))

# --- Markers with Elevation Tooltips ---
point_group = FeatureGroup(name="PointMarkers", show=True)
for i, ((lon, lat), z) in enumerate(zip(latlon_points, elevations)):
    lat_dms = format_dms(lat, is_lat=True)
    lon_dms = format_dms(lon, is_lat=False)
    z_disp = f"{z} m" if z is not None else "N/A"
    point_group.add_child(folium.Marker(
        location=[lat, lon],
        tooltip=f"{lat_dms}, {lon_dms} | Elev: {z_disp}",
        icon=folium.DivIcon(html=f"""
            <div style="font-size: 10pt; background: white; border: 1px solid black;
                border-radius: 50%; width: 24px; height: 24px; text-align: center;
                line-height: 24px; font-weight: bold;">
                {i+1}
            </div>
        """)
    ))
m.add_child(point_group)

# --- Print and Toggle Buttons ---
extra_html = """
<style>
@media print { #button-container, #toggle-button { display: none; } }
#toggle-button {
    margin-top: 10px;
    background-color: #444;
    color: white;
    border: none;
    padding: 8px 14px;
    font-size: 13px;
    border-radius: 5px;
    cursor: pointer;
    box-shadow: 1px 1px 4px rgba(0,0,0,0.4);
}
</style>
<script>
let pointsVisible = true;
function printMap() { window.print(); }
function togglePoints() {
    const markers = document.querySelectorAll('.leaflet-marker-icon, .leaflet-tooltip');
    markers.forEach(el => el.style.display = pointsVisible ? 'none' : 'block');
    pointsVisible = !pointsVisible;
    document.getElementById('toggle-button').innerText = pointsVisible ? 'Hide Points' : 'Show Points';
}
</script>
<div id="button-container" style="position: fixed; top: 10px; right: 10px; z-index: 9999;">
  <button onclick="printMap()" style="
    background-color: darkgreen;
    color: white;
    border: none;
    padding: 10px 16px;
    font-size: 13px;
    border-radius: 5px;
    cursor: pointer;
    box-shadow: 1px 1px 4px rgba(0,0,0,0.4);">
    🖨️ Print Map
  </button><br>
  <button id="toggle-button" onclick="togglePoints()">Hide Points</button>
</div>
"""
m.get_root().html.add_child(folium.Element(extra_html))

# --- Save and Open ---
file_path = "road_center_with_elevations.html"
m.save(file_path)
webbrowser.open("file://" + os.path.realpath(file_path))
