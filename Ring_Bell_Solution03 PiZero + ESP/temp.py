import requests
import json

def fetch_map_id(robot_ip):
    map_id_url = f"http://{robot_ip}:8090/chassis/current-map"
    try:
        response = requests.get(map_id_url, timeout=5)
        if response.status_code == 200:
            map_data = response.json()
            map_id = map_data['id']
            print(f"Map ID for robot {robot_ip}: {map_id}")
            return map_id
        else:
            print(f"Failed to fetch map ID for robot {robot_ip}. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching map ID for robot {robot_ip}: {e}")
        return None

def fetch_point_name(robot_ip, map_id, coordinates):
    map_details_url = f"http://{robot_ip}:8090/maps/{map_id}"
    try:
        response = requests.get(map_details_url, timeout=5)
        if response.status_code == 200:
            map_details = response.json()
            overlays = map_details['overlays']
            overlays_data = json.loads(overlays)

            print(f"Fetched map details for robot {robot_ip}, map ID {map_id}:")
            for feature in overlays_data['features']:
                feature_coordinates = feature['geometry']['coordinates']
                if feature_coordinates == coordinates:
                    point_name = feature['properties']['name']
                    print(f"Point Name for coordinates {coordinates}: {point_name}")
                    return point_name
            print(f"No matching point found for coordinates {coordinates} in map {map_id}")
        else:
            print(f"Failed to fetch map details for robot {robot_ip}, map ID {map_id}. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching point name for robot {robot_ip}, map ID {map_id}: {e}")
        return None

# Example usage:
robot_ip = '192.168.1.87'  # Replace with your robot IP
coordinates = [0.6505813155643047, 19.137661152892633]  # Example coordinates
map_id = fetch_map_id(robot_ip)

if map_id:
    fetch_point_name(robot_ip, map_id, coordinates)
