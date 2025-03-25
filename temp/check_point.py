import requests
import json

# Define target_x and target_y
target_x = 0.7875
target_y = 7.170000000000001

# Round the coordinates to 4 decimal places
target_x = round(target_x, 4)
target_y = round(target_y, 4)

# Form the target_coordinates array using the rounded values
target_coordinates = [target_x, target_y]

# Step 1: Get the current map ID
map_id_url = "http://192.168.1.84:8090/chassis/current-map"
response = requests.get(map_id_url)

if response.status_code == 200:
    map_data = response.json()
    map_id = map_data['id']
    print(f"Map ID: {map_id}")
else:
    print(f"Failed to retrieve map ID. Status Code: {response.status_code}")
    exit()

# Step 2: Get the map details using the map ID
map_details_url = f"http://192.168.1.84:8090/maps/{map_id}"
response = requests.get(map_details_url)

if response.status_code == 200:
    map_details = response.json()
    overlays = map_details['overlays']
    
    # Parse overlays JSON string
    overlays_data = json.loads(overlays)
    
    # Step 3: Search for coordinates and print the corresponding name
    for feature in overlays_data['features']:
        coordinates = feature['geometry']['coordinates']
        
        # Round the feature coordinates to handle any extra zeroes
        rounded_coordinates = [round(coordinate, 4) for coordinate in coordinates]
        
        # Compare the rounded coordinates
        if rounded_coordinates == target_coordinates:
            name = feature['properties']['name']
            print(f"Coordinates {target_coordinates} corresponds to point name: {name}")
            break
    else:
        print(f"Coordinates {target_coordinates} not found in the map overlays.")
else:
    print(f"Failed to retrieve map details. Status Code: {response.status_code}")
