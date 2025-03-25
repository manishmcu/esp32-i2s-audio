import json
import math
import requests
import websocket
import time
import threading
import signal
import sys
import socket
import subprocess
from flask import Flask, jsonify
from concurrent.futures import ThreadPoolExecutor

# Flask setup
app = Flask(__name__)

# Global variables
robots_status = {}

# Function to calculate Euclidean distance
def calculate_distance(x1, y1, x2, y2):
    return round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 4)

# Function to get the local IP address of the Pi
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.254.254.254', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    return local_ip

# Function to extract the network base IP from the local IP
def get_base_ip(local_ip):
    base_ip = '.'.join(local_ip.split('.')[:3]) + '.0'
    return base_ip

# Function to run nmap command and get live IP addresses
def get_ip_addresses(base_ip):
    result = subprocess.run(["nmap", "-sn", "-T4", "-n", f"{base_ip}/24"], capture_output=True, text=True)
    ip_addresses = []
    for line in result.stdout.splitlines():
        if "Nmap scan report for" in line:
            parts = line.split()
            if len(parts) > 4 and parts[4].count('.') == 3:
                ip_addresses.append(parts[4])
    return ip_addresses

# Function to check if the IP is a robot and get its SN
def check_if_robot(ip):
    url = f"http://{ip}:8090/device/info"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            device_data = response.json()
            if "device" in device_data:
                sn = device_data["device"].get("sn", "Unknown")
                return ip, sn
    except requests.RequestException:
        return ip, None  # If no SN is found or error occurs, return None for SN

# Initialize executor for parallel tasks
executor = ThreadPoolExecutor(max_workers=4)

def fetch_latest_move(robot_ip):
    moves_url = f"http://{robot_ip}:8090/chassis/moves"
    response = requests.get(moves_url)
    if response.status_code != 200:
        return None
    moves_data = response.json()
    return moves_data[0] if moves_data else None

def fetch_move_details(robot_ip, move_id):
    move_details_url = f"http://{robot_ip}:8090/chassis/moves/{move_id}"
    response = requests.get(move_details_url)
    if response.status_code != 200:
        return None
    return response.json()

def check_point_match(robot_ip, target_x, target_y):
    if target_x is None or target_y is None:
        return "None"
    
    target_coordinates = [float(f"{target_x:.4f}"), float(f"{target_y:.4f}")]
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

                if isinstance(coordinates[0], list):  
                    # If it's a nested list, take the first pair
                    coordinates = coordinates[0]

                formatted_coordinates = [float(f"{c:.4f}") for c in coordinates]

                if formatted_coordinates == target_coordinates:
                    return feature['properties']['name']
    return "None"


def on_message(ws, message, robot_ip):
    global robots_status

    data = json.loads(message)
    if data.get("topic") == "/tracked_pose":
        current_pos_x, current_pos_y = data["pos"]
        if robot_ip in robots_status:
            robot = robots_status[robot_ip]
            if robot['current_target_x'] is not None and robot['current_target_y'] is not None:
                distance = calculate_distance(current_pos_x, current_pos_y, robot['current_target_x'], robot['current_target_y'])
                new_arrive_stat = "moving"
                if robot['arrived']:
                    new_arrive_stat = "arrived"
                elif distance < robot['near_off']:
                    new_arrive_stat = "near"
                    move_details = fetch_move_details(robot_ip, robot['current_move_id'])
                    if move_details and move_details.get("state") == "succeeded":
                        new_arrive_stat = "arrived"

                if new_arrive_stat != robot['arrive_stat_last']:
                    robot['arrive_stat'] = new_arrive_stat
                    robot['arrive_stat_last'] = new_arrive_stat
                    print(f"Arrive Status changed for {robot_ip}: {new_arrive_stat}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")
    reconnect_to_websocket(ws)

def on_open(ws):
    ws.send(json.dumps({"enable_topic": "/tracked_pose"}))

def reconnect_to_websocket(ws):
    global robots_status
    while True:
        print("Reconnecting to WebSocket...")
        for robot_ip in robots_status.keys():
            ws = websocket.WebSocketApp(
                f"ws://{robot_ip}:8090/ws/v2/topics",
                on_message=lambda ws, msg: on_message(ws, msg, robot_ip),
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = on_open
            ws.run_forever()
            time.sleep(0.1)

def check_for_new_move(robot_ip):
    global robots_status
    while True:
        future = executor.submit(fetch_latest_move, robot_ip)
        latest_move = future.result()

        if latest_move:
            move_id = latest_move["id"]
            state = latest_move.get("state", "")

            if move_id != robots_status[robot_ip]['current_move_id']:
                robots_status[robot_ip]['current_move_id'] = move_id
                move_details = fetch_move_details(robot_ip, move_id)
                if move_details:
                    robots_status[robot_ip]['current_target_x'] = move_details.get("target_x")
                    robots_status[robot_ip]['current_target_y'] = move_details.get("target_y")

                    arrive_stat = "arrived" if state == "succeeded" else "in_progress"
                    robots_status[robot_ip]['arrived'] = state == "succeeded"

                    point_id = check_point_match(robot_ip, robots_status[robot_ip]['current_target_x'], robots_status[robot_ip]['current_target_y'])
                    robots_status[robot_ip]['point_id'] = point_id
                    print(f"New Move for {robot_ip}: Updated point_id: {point_id}")

        time.sleep(0.1)  

@app.route('/ring_bell')
def status():
    return jsonify(robots_status)

def main():
    # Get local IP and base IP for scanning
    local_ip = get_local_ip()
    base_ip = get_base_ip(local_ip)

    # Scan for live robots on the network
    ip_addresses = get_ip_addresses(base_ip)
    robot_ips = [ip for ip in ip_addresses if check_if_robot(ip)[1]]  # Only include robot IPs

    # Initialize robot statuses
    for robot_ip in robot_ips:
        sn = check_if_robot(robot_ip)[1]
        robots_status[robot_ip] = {
            'robot_sn': sn,
            'robot_ip': robot_ip,
            'status': 'active',
            'arrive_stat': 'moving',
            'point_id': 'Unknown',
            'current_move_id': None,
            'current_target_x': None,
            'current_target_y': None,
            'arrived': False,
            'arrive_stat_last': 'moving',
            'near_off': 2.0
        }

    # Starting threads for each robot
    for robot_ip in robot_ips:
        threading.Thread(target=check_for_new_move, args=(robot_ip,), daemon=True).start()
        threading.Thread(target=reconnect_to_websocket, args=(None,), daemon=True).start()

    app.run(host="0.0.0.0", port=5000)

def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
