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

# Flask setup
app = Flask(__name__)
point_id = "None"  
arrive_stat = "moving"

# Function to calculate Euclidean distance
def calculate_distance(x1, y1, x2, y2):
    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 4)

# Base URLs
robot_ip = "192.168.1.84" 
moves_url = f"http://{robot_ip}:8090/chassis/moves"
ws_url = f"ws://{robot_ip}:8090/ws/v2/topics"

# Initialize variables
current_move_id = None
current_target_x = None
current_target_y = None
current_pos_x = None
current_pos_y = None
near_off = 2.0  
arrived = False  
arrive_stat_last = "moving"  

executor = ThreadPoolExecutor(max_workers=4)

def fetch_latest_move():
    response = requests.get(moves_url)
    if response.status_code != 200:
        return None
    moves_data = response.json()
    return moves_data[0] if moves_data else None

def fetch_move_details(move_id):
    move_details_url = f"{moves_url}/{move_id}"
    response = requests.get(move_details_url)
    if response.status_code != 200:
        return None
    return response.json()

def check_point_match():
    global current_target_x, current_target_y
    if current_target_x is None or current_target_y is None:
        return "None"
    
    target_coordinates = [round(current_target_x, 4), round(current_target_y, 4)]
    map_id_url = f"http://{robot_ip}:8090/chassis/current-map"
    response = requests.get(map_id_url)

    if response.status_code == 200:
        map_data = response.json()
        map_id = map_data['id']
        map_details_url = f"http://{robot_ip}:8090/maps/{map_id}"
        response = requests.get(map_details_url)

        if response.status_code == 200:
            map_details = response.json()
            overlays = map_details['overlays']
            overlays_data = json.loads(overlays)

            for feature in overlays_data['features']:
                coordinates = feature['geometry']['coordinates']
                rounded_coordinates = [round(c, 4) for c in coordinates]

                if rounded_coordinates == target_coordinates:
                    return feature['properties']['name']
    return "None"

def on_message(ws, message):
    global current_pos_x, current_pos_y, current_move_id, current_target_x, current_target_y, arrive_stat, arrived, point_id, arrive_stat_last

    data = json.loads(message)

    if data.get("topic") == "/tracked_pose":
        current_pos_x, current_pos_y = data["pos"]

        if current_target_x is not None and current_target_y is not None:
            distance = calculate_distance(current_pos_x, current_pos_y, current_target_x, current_target_y)

            new_arrive_stat = "moving"
            if arrived:
                new_arrive_stat = "arrived"
            elif distance < near_off:
                new_arrive_stat = "near"
                move_details = fetch_move_details(current_move_id)
                if move_details and move_details.get("state") == "succeeded":
                    new_arrive_stat = "arrived"

            if new_arrive_stat != arrive_stat_last:
                arrive_stat = new_arrive_stat
                arrive_stat_last = new_arrive_stat
                print(f"Arrive Status changed: {arrive_stat}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")
    reconnect_to_websocket()

def on_open(ws):
    ws.send(json.dumps({"enable_topic": "/tracked_pose"}))

def check_for_new_move():
    global current_move_id, current_target_x, current_target_y, arrived, point_id
    while True:
        future = executor.submit(fetch_latest_move)
        latest_move = future.result()

        if latest_move:
            move_id = latest_move["id"]
            state = latest_move.get("state", "")

            if move_id != current_move_id:
                current_move_id = move_id
                move_details = fetch_move_details(move_id)
                if move_details:
                    current_target_x = move_details.get("target_x")
                    current_target_y = move_details.get("target_y")

                    arrive_stat = "arrived" if state == "succeeded" else "in_progress"
                    arrived = state == "succeeded"

                    point_id = check_point_match()
                    print(f"New Move ID: {move_id}. Updated point_id: {point_id}")

        time.sleep(0.1)  

def reconnect_to_websocket():
    global ws
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
        time.sleep(0.1)

@app.route('/status')
def status():
    return jsonify({"point_id": point_id, "arrive_stat": arrive_stat})

def main():
    move_thread = threading.Thread(target=check_for_new_move, daemon=True)
    move_thread.start()

    threading.Thread(target=reconnect_to_websocket, daemon=True).start()

    app.run(host="0.0.0.0", port=5000)

def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
