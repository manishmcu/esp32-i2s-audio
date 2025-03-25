import json
import math
import requests
import websocket
import time
import threading
import RPi.GPIO as GPIO

# GPIO setup for LED control
LED_PIN = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

# Function to calculate Euclidean distance
def calculate_distance(x1, y1, x2, y2):
    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 4)

# Initialize variables
current_move_id = None
current_target_x = None
current_target_y = None
current_pos_x = None
current_pos_y = None
near_off = 4  # Set near threshold to 4 meters
arrive_stat = "moving"  # Default state is "moving"
arrived = False  # Flag to ensure we don't overwrite the "arrived" state
last_arrive_stat = "moving"  # To track the last printed arrive_stat
robot_ip = "192.168.65.119"  # Set your robot IP
provided_point_id = "240"  # Example provided point ID for comparison
point_name = ""

# Base URLs
base_url = f"http://{robot_ip}:8090"
moves_url = f"http://{robot_ip}:8090/chassis/moves"
ws_url = f"ws://{robot_ip}:8090/ws/v2/topics"

# LED Blinking Control Thread
def led_blinking_thread():
    global arrive_stat
    while True:
        if arrive_stat == "arrived" and point_name == provided_point_id:
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.5)  # LED ON for 500ms
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.5)  # LED OFF for 500ms
        else:
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off the LED if not arrived
            time.sleep(1)

# Fetch map ID dynamically
def fetch_map_id():
    url = f"http://{robot_ip}:8090/chassis/current-map"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            map_data = response.json()
            map_id = map_data['id']
            print(f"Map ID: {map_id}")
            return map_id
        else:
            print(f"Failed to retrieve map ID. Status Code: {response.status_code}")
            exit()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching map ID: {e}")
        exit()

# Function to fetch map details using map_id
def fetch_map_details(map_id):
    url = f"http://{robot_ip}:8090/maps/{map_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            map_details = response.json()
            overlays = map_details['overlays']
            
            # Parse overlays JSON string
            overlays_data = json.loads(overlays)
            return overlays_data
        else:
            print(f"Failed to retrieve map details. Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching map details: {e}")
    return None

# Function to search for coordinates in overlays
def search_coordinates_in_overlays(target_coordinates, overlays_data):
    for feature in overlays_data['features']:
        coordinates = feature['geometry']['coordinates']
        
        # Check if all coordinates are numeric before formatting
        if all(isinstance(coord, (int, float)) for coord in coordinates):
            # Convert coordinates to string with 4 decimals for comparison
            rounded_coordinates = [f"{coordinate:.4f}" for coordinate in coordinates]
            target_coords_str = [f"{coord:.4f}" for coord in target_coordinates]

            # Compare the coordinates as strings
            if rounded_coordinates == target_coords_str:
                name = feature['properties']['name']
                print(f"Coordinates {target_coordinates} corresponds to point name: {name}")
                return name
        else:
            print(f"Warning: Non-numeric coordinate found in feature {feature}")
    
    print(f"Coordinates {target_coordinates} not found in the map overlays.")
    return None


# Fetch the latest move details
def fetch_latest_move():
    try:
        response = requests.get(moves_url)
        if response.status_code == 200:
            moves = response.json()
            # Assuming the most recent move is the first one in the list
            latest_move = moves[0] if moves else None
            return latest_move
        else:
            print(f"Failed to retrieve latest move. Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching latest move: {e}")
    return None

# Function to fetch move details using move_id
def fetch_move_details(move_id):
    url = f"http://{robot_ip}:8090/chassis/moves/{move_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            move_details = response.json()
            return move_details
        else:
            print(f"Failed to retrieve move details. Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching move details: {e}")
    return None

# Function to check the point ID when robot is close to the target
def check_for_point_id(arrival_status, target_coordinates):
    global point_name
    if arrival_status == "arrived":
        # Fetch map ID and then map details
        map_id = fetch_map_id()
        overlays_data = fetch_map_details(map_id)
        if overlays_data:
            point_name = search_coordinates_in_overlays(target_coordinates, overlays_data)
            if point_name:
                print(f"Point ID: {point_name}")
                if point_name == provided_point_id:
                    GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on the LED if point matches
                    print(f"Point ID {provided_point_id} matched! LED on pin {LED_PIN} is now ON.")
                else:
                    GPIO.output(LED_PIN, GPIO.LOW)  # Turn off the LED if point does not match
            else:
                print("Point ID: none")

# WebSocket handlers
def on_message(ws, message):
    global current_pos_x, current_pos_y, current_move_id, current_target_x, current_target_y, robot_ip, arrive_stat, arrived, last_arrive_stat

    # Parse the WebSocket message
    data = json.loads(message)
    
    if data.get("topic") == "/tracked_pose":
        current_pos = data["pos"]
        current_pos_x, current_pos_y = current_pos

        # Calculate the distance to the target
        if current_target_x is not None and current_target_y is not None:
            distance = calculate_distance(current_pos_x, current_pos_y, current_target_x, current_target_y)

            # Check if the "state" is succeeded and set arrive_stat
            if current_move_id is not None:
                move_details = fetch_move_details(current_move_id)
                if move_details:
                    state = move_details.get("state", "")
                    
                    # Set arrive_stat based on move state
                    if state == "succeeded" and not arrived:
                        arrive_stat = "arrived"
                        arrived = True
                        print(f"Move {current_move_id} has succeeded! Robot has arrived.")

            # Set arrive_stat based on the distance, priority to "arrived"
            if arrived:
                arrive_stat = "arrived"
            elif distance < near_off:
                arrive_stat = "near"
            else:
                arrive_stat = "moving"

            # Print status only if arrive_stat has changed or "near" status
            if arrive_stat != last_arrive_stat or arrive_stat == "near":
                print(f"Robot IP: {robot_ip}, Current Position: ({current_pos_x:.4f}, {current_pos_y:.4f}), Target Position: ({current_target_x:.4f}, {current_target_y:.4f}), Distance: {distance:.4f} meters, Status: {arrive_stat}")
                last_arrive_stat = arrive_stat  # Update the last arrived state to avoid repeated prints

                # Check point ID when robot arrives at target
                check_for_point_id(arrive_stat, [current_target_x, current_target_y])

# WebSocket handlers
def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")
    reconnect_to_websocket()

def on_open(ws):
    # Enable the tracked_pose topic
    enable_topic_message = {"enable_topic": "/tracked_pose"}
    ws.send(json.dumps(enable_topic_message))

# Function to monitor the latest move command and update if necessary
def check_for_new_move():
    global current_move_id, current_target_x, current_target_y, current_pos_x, current_pos_y, robot_ip, arrive_stat, arrived, last_arrive_stat
    while True:
        # Fetch the latest move command every 2 seconds
        latest_move = fetch_latest_move()
        if latest_move:
            move_id = latest_move["id"]
            state = latest_move.get("state", "")

            # Reset GPIO immediately when new command arrives
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED at the start

            # Check if there's a new move command
            if move_id != current_move_id:
                current_move_id = move_id

                # Fetch new target coordinates
                move_details = fetch_move_details(move_id)
                if move_details:
                    # Update all variables and reset the calculations
                    current_target_x = move_details.get("target_x")
                    current_target_y = move_details.get("target_y")
                    current_pos_x = None  # Reset position
                    current_pos_y = None  # Reset position

                    # Check point ID immediately when a new move comes
                    check_for_point_id(arrive_stat, [current_target_x, current_target_y])

                    # Check if state is "succeeded" and set arrive_stat to "arrived"
                    if state == "succeeded":
                        arrive_stat = "arrived"
                        arrived = True  # Set the flag to avoid overwriting
                        print(f"Move {move_id} has succeeded! Robot has arrived.")
                    else:
                        arrive_stat = "in_progress"
                        arrived = False  # Reset the arrived flag if the move is still in progress
                        print(f"Move {move_id} is in progress.")

        # Sleep before checking for new move commands (every 2 seconds)
        time.sleep(2)  # 2 second interval for fetching move data

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
        time.sleep(1)  # Wait for 1 second before trying to reconnect

# Main function to start the WebSocket and move checking concurrently
def main():
    global last_arrive_stat
    last_arrive_stat = arrive_stat  # Initialize the last arrive state

    # Start the LED blinking thread
    led_thread = threading.Thread(target=led_blinking_thread)
    led_thread.daemon = True  # Ensures the thread will exit when the program exits
    led_thread.start()

    # Start the move checking function in a separate thread
    move_thread = threading.Thread(target=check_for_new_move)
    move_thread.daemon = True  # Ensures the thread will exit when the program exits
    move_thread.start()

    # Start WebSocket connection and keep it running indefinitely
    reconnect_to_websocket()

# Run the main function
if __name__ == "__main__":
    main()
