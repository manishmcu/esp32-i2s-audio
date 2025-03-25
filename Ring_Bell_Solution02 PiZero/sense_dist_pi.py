import json
import math
import requests
import websocket
import time
import threading
import signal
import sys

# Function to calculate Euclidean distance
def calculate_distance(x1, y1, x2, y2):
    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 4)

# Base URLs
base_url = "http://192.168.1.87:8090"
moves_url = f"{base_url}/chassis/moves"
ws_url = "ws://192.168.1.87:8090/ws/v2/topics"

# Initialize variables
current_move_id = None
current_target_x = None
current_target_y = None
current_pos_x = None
current_pos_y = None
near_off = 4  # Set near threshold to 4 meters
robot_ip = "192.168.1.87"  # Set your robot IP
arrive_stat = "moving"  # Default state is "moving"
arrived = False  # Flag to ensure we don't overwrite the "arrived" state
last_arrive_stat = "moving"  # To track the last printed arrive_stat

# Step 1: Get the latest move command
def fetch_latest_move():
    try:
        response = requests.get(moves_url)
        if response.status_code == 200:
            moves_data = response.json()
            if moves_data:
                return moves_data[0]  # Assuming the first entry is the latest
    except requests.exceptions.RequestException as e:
        print(f"Error fetching move: {e}")
    return None

# Step 2: Fetch target location for the move
def fetch_move_details(move_id):
    move_details_url = f"{moves_url}/{move_id}"
    try:
        response = requests.get(move_details_url)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching move details: {e}")
    return None

# Step 3: Connect to the WebSocket and enable the tracked_pose topic
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

# WebSocket handlers
def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")
    # Try to reconnect when the connection is closed
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

    # Start the move checking function in a separate thread
    move_thread = threading.Thread(target=check_for_new_move)
    move_thread.daemon = True  # Ensures the thread will exit when the program exits
    move_thread.start()

    # Start WebSocket connection and keep it running indefinitely
    reconnect_to_websocket()

# Graceful exit on Ctrl+C
def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    sys.exit(0)

# Register the signal handler for Ctrl+C (SIGINT)
signal.signal(signal.SIGINT, signal_handler)

# Run the main function
if __name__ == "__main__":
    main()
