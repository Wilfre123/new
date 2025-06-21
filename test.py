import leafmap.foliumap as leafmap
import folium

# --- Coordinates ---
point1 = (9.853383158, 122.877036670)  # (lat, lon)
point2 = (9.854100000, 122.878500000)  # (lat, lon)

# --- Create Leafmap map ---
center_lat = (point1[0] + point2[0]) / 2
center_lon = (point1[1] + point2[1]) / 2
m = leafmap.Map(center=(center_lat, center_lon), zoom=17)

# --- Add markers ---
m.add_marker(location=point1, popup="📍 Point 1")
m.add_marker(location=point2, popup="📍 Point 2")

# --- Add polyline using folium directly ---
folium.PolyLine(locations=[point1, point2], color="green", weight=4).add_to(m)

# --- Save to HTML ---
m.to_html("leafmap_line_between_points.html")
print("✅ Map saved as 'leafmap_line_between_points.html'")
