import json
import math
import requests
import websocket
import time
import threading
import signal
import sys
from flask import Flask, jsonify
from concurrent.futures import ThreadPoolExecutor

# Flask setup for local server
app = Flask(__name__)
point_id = "None"  # Default value
arrive_stat = "moving"  # Default state

# Function to calculate Euclidean distance
def calculate_distance(x1, y1, x2, y2):
    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 4)

# Base URLs
base_url = "http://192.168.1.84:8090"
moves_url = f"{base_url}/chassis/moves"
ws_url = "ws://192.168.1.84:8090/ws/v2/topics"

# Initialize variables
current_move_id = None
current_target_x = None
current_target_y = None
current_pos_x = None
current_pos_y = None
near_off = 1.0  # Ensuring that `near_off` is defined
robot_ip = "192.168.1.84"  # Set your robot IP
arrived = False  # Flag to ensure we don't overwrite the "arrived" state

# Function to check if target coordinates match any predefined point
def check_point_match():
    global current_target_x, current_target_y
    if current_target_x is not None and current_target_y is not None:
        target_coordinates = [round(current_target_x, 4), round(current_target_y, 4)]
        
        map_id_url = "http://192.168.1.84:8090/chassis/current-map"
        response = requests.get(map_id_url)

        if response.status_code == 200:
            map_data = response.json()
            map_id = map_data['id']
            print(f"Map ID: {map_id}")

            # Fetch map details using map ID
            map_details_url = f"http://192.168.1.84:8090/maps/{map_id}"
            response = requests.get(map_details_url)

            if response.status_code == 200:
                map_details = response.json()
                overlays = map_details['overlays']
                overlays_data = json.loads(overlays)

                # Search for coordinates and return the corresponding name
                for feature in overlays_data['features']:
                    coordinates = feature['geometry']['coordinates']
                    rounded_coordinates = [round(coordinate, 4) for coordinate in coordinates]

                    if rounded_coordinates == target_coordinates:
                        return feature['properties']['name']
                return "None"  # Explicit return of "None" if no match found
            else:
                print(f"Failed to retrieve map details. Status Code: {response.status_code}")
        else:
            print(f"Failed to retrieve map ID. Status Code: {response.status_code}")
    return "None"  # Default return if not found

# WebSocket handlers
def on_message(ws, message):
    global current_pos_x, current_pos_y, current_move_id, current_target_x, current_target_y, robot_ip, arrive_stat, arrived, point_id

    # Parse the WebSocket message
    data = json.loads(message)

    if data.get("topic") == "/tracked_pose":
        current_pos = data["pos"]
        current_pos_x, current_pos_y = current_pos

        # Calculate the distance to the target
        if current_target_x is not None and current_target_y is not None:
            distance = calculate_distance(current_pos_x, current_pos_y, current_target_x, current_target_y)

            # Print the calculated distance for debugging
            print(f"Calculated Distance: {distance:.4f} meters")

            # Check if the "state" is succeeded and set arrive_stat
            if current_move_id is not None:
                move_details = fetch_move_details(current_move_id)
                if move_details:
                    state = move_details.get("state", "")

                    if state == "succeeded" and not arrived:
                        arrive_stat = "arrived"
                        arrived = True
                        point_id = check_point_match()  # Update point_id when the move succeeds
                        print(f"Move {current_move_id} has succeeded! Robot has arrived. Point ID: {point_id}")

            # Set arrive_stat based on the distance
            if arrived:
                arrive_stat = "arrived"
            elif distance < near_off:
                arrive_stat = "near"
            else:
                arrive_stat = "moving"

            # Print status with distance and arrive_stat
            print(f"Robot IP: {robot_ip}, Current Position: ({current_pos_x:.4f}, {current_pos_y:.4f}), Target Position: ({current_target_x:.4f}, {current_target_y:.4f}), Distance: {distance:.4f} meters, Status: {arrive_stat}")

# WebSocket handlers for errors and connection close
def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")
    reconnect_to_websocket()

def on_open(ws):
    # Enable the tracked_pose topic
    enable_topic_message = {"enable_topic": "/tracked_pose"}
    ws.send(json.dumps(enable_topic_message))

# Use ThreadPoolExecutor for concurrent HTTP requests
executor = ThreadPoolExecutor(max_workers=4)

def fetch_latest_move():
    response = requests.get(moves_url)
    if response.status_code != 200:
        print("Error fetching moves data")
        return None
    moves_data = response.json()
    if moves_data:
        return moves_data[0]  # Assuming the first entry is the latest
    return None

def fetch_move_details(move_id):
    move_details_url = f"{moves_url}/{move_id}"
    response = requests.get(move_details_url)
    if response.status_code != 200:
        print("Error fetching move details")
        return None
    return response.json()

def check_for_new_move():
    global current_move_id, current_target_x, current_target_y, current_pos_x, current_pos_y, robot_ip, arrive_stat, arrived, point_id
    while True:
        # Fetch the latest move command asynchronously
        future = executor.submit(fetch_latest_move)
        latest_move = future.result()  # Wait for the result

        if latest_move:
            move_id = latest_move["id"]
            state = latest_move.get("state", "")

            # Check if there's a new move command
            if move_id != current_move_id:
                current_move_id = move_id
                move_details = fetch_move_details(move_id)
                if move_details:
                    # Update variables and reset calculations
                    current_target_x = move_details.get("target_x")
                    current_target_y = move_details.get("target_y")
                    current_pos_x = None  # Reset position
                    current_pos_y = None  # Reset position

                    # Update arrive_stat based on state
                    if state == "succeeded":
                        arrive_stat = "arrived"
                        arrived = True
                    else:
                        arrive_stat = "in_progress"
                        arrived = False

                    # Update point_id only when a new move is received
                    point_id = check_point_match()
                    print(f"New Move ID: {move_id}. Updated point_id: {point_id}")

        time.sleep(0.3)  # Further reduced sleep for faster updates

# Reconnect to the WebSocket if the connection is closed
def reconnect_to_websocket():
    while True:
        print("Reconnecting to WebSocket...")
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open
        ws.run_forever()
        time.sleep(0.3)  # Reduced the sleep time for faster reconnecting

# Flask route to serve point_id and arrive_stat
@app.route('/status')
def status():
    return jsonify({"point_id": point_id, "arrive_stat": arrive_stat})

# Main function to start WebSocket, move checking, and Flask server concurrently
def main():
    # Start the move checking function in a separate thread
    move_thread = threading.Thread(target=check_for_new_move)
    move_thread.daemon = True  # Ensures the thread will exit when the program exits
    move_thread.start()

    # Start WebSocket connection
    threading.Thread(target=reconnect_to_websocket, daemon=True).start()

    # Start Flask app
    app.run(host="0.0.0.0", port=5000)

# Graceful exit on Ctrl+C
def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    sys.exit(0)

# Register the signal handler for Ctrl+C (SIGINT)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
