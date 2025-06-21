import folium
from pyproj import Transformer
import webbrowser, os
import math

# --- UTM Zone 51N Coordinates ---
utm_points = [
    (486261.21, 1087959.9),
    (485907.87, 1088478.4)
]

# --- Convert UTM to Lat/Lon ---
transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
latlon_points = [transformer.transform(x, y) for x, y in utm_points]

# --- DMS Conversion Functions ---
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

# --- Center Map ---
center_lat = sum(lat for _, lat in latlon_points) / len(latlon_points)
center_lon = sum(lon for lon, _ in latlon_points) / len(latlon_points)
m = folium.Map(location=[center_lat, center_lon], zoom_start=17, control_scale=True)

# --- Draw Main Centerline ---
folium.PolyLine([(lat, lon) for lon, lat in latlon_points], color='blue', weight=4).add_to(m)

# --- Offset Road Edges ---
offset_distance = 3  # meters
left_offsets = []
right_offsets = []

for i in range(len(utm_points) - 1):
    x1, y1 = utm_points[i]
    x2, y2 = utm_points[i + 1]

    # Direction vector
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)

    # Normalize and get perpendicular
    ux = -dy / length
    uy = dx / length

    # Apply offset to both points (left and right)
    left1 = (x1 + ux * offset_distance, y1 + uy * offset_distance)
    left2 = (x2 + ux * offset_distance, y2 + uy * offset_distance)
    right1 = (x1 - ux * offset_distance, y1 - uy * offset_distance)
    right2 = (x2 - ux * offset_distance, y2 - uy * offset_distance)

    left_offsets.append(transformer.transform(*left1)[::-1])
    left_offsets.append(transformer.transform(*left2)[::-1])
    right_offsets.append(transformer.transform(*right1)[::-1])
    right_offsets.append(transformer.transform(*right2)[::-1])

# Draw road edges
folium.PolyLine(left_offsets, color='gray', weight=2).add_to(m)
folium.PolyLine(right_offsets, color='gray', weight=2).add_to(m)

# --- Sidebar with Toggle ---
sidebar_html = """
<div style="
    position: fixed;
    top: 20px;
    left: 70px;
    width: 160px;
    background: white;
    padding: 10px;
    border: 1px solid black;
    border-radius: 5px;
    font-family: Arial;
    font-size: 12px;
    z-index: 9999;
    max-height: 90vh;
    overflow-y: auto;" id="sidebar">
    
    <label><b>Coordinate View</b></label>
    <select onchange="toggleFormat(this.value)" style="margin-bottom: 10px; width: 100%;">
        <option value="dms">DMS</option>
        <option value="utm">UTM (E/N)</option>
        <option value="ne">N/E</option>
    </select>
    <div id="coord-list">
"""

# Add coordinates for both DMS, UTM and Northing/Easting format
for i, ((lon, lat), (x, y)) in enumerate(zip(latlon_points, utm_points)):
    lat_dms = format_dms(lat, is_lat=True)
    lon_dms = format_dms(lon, is_lat=False)
    
    sidebar_html += f"""
    <div>
        <b>Point {i+1}</b><br>
        <span class="coord-dms">{lat_dms}<br>{lon_dms}</span>
        <span class="coord-utm" style="display:none;">E: {x:.2f}<br>N: {y:.2f}</span>
        <span class="coord-ne" style="display:none;">N: {y:.2f}<br>E: {x:.2f}</span>
    </div>
    <hr style="margin:4px 0;">
    """

sidebar_html += """
    </div>
</div>

<script>
function toggleFormat(fmt) {
    const dmsElems = document.querySelectorAll('.coord-dms');
    const utmElems = document.querySelectorAll('.coord-utm');
    const neElems = document.querySelectorAll('.coord-ne');
    
    // Hide all and show the selected one
    dmsElems.forEach(el => el.style.display = (fmt === 'dms' ? 'block' : 'none'));
    utmElems.forEach(el => el.style.display = (fmt === 'utm' ? 'block' : 'none'));
    neElems.forEach(el => el.style.display = (fmt === 'ne' ? 'block' : 'none'));
}
</script>
"""

m.get_root().html.add_child(folium.Element(sidebar_html))

# --- Markers ---
for i, (lon, lat) in enumerate(latlon_points):
    lat_dms = format_dms(lat, is_lat=True)
    lon_dms = format_dms(lon, is_lat=False)
    folium.Marker(
        location=[lat, lon],
        tooltip=f"{lat_dms}, {lon_dms}",
        icon=folium.DivIcon(html=f"""
            <div style="
                font-size: 10pt;
                background: white;
                border: 1px solid black;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                text-align: center;
                line-height: 24px;
                font-weight: bold;">
                {i+1}
            </div>
        """)
    ).add_to(m)

# --- Print Button Only ---
button_html = """
<style>
@media print {
  #button-container {
    display: none;
  }
}
</style>
<script>
function printMap() {
    window.print();
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
  </button>
</div>
"""

m.get_root().html.add_child(folium.Element(button_html))

# --- Save and Open ---
file_path = "road_center_with_edges.html"
m.save(file_path)
webbrowser.open("file://" + os.path.realpath(file_path))
