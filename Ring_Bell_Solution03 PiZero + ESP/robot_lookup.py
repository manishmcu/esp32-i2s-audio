import subprocess
import requests
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
import pytz

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
        return ip, None

# Function to check if a robot is active
def check_robot_status(robot_ip):
    url = f"http://{robot_ip}:8090/chassis/moves"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            move_data = response.json()
            if move_data:
                last_move = move_data[0]  # Assuming the latest move is the first in the list
                create_time = last_move["create_time"]
                state = last_move["state"]
                
                # Convert create_time from UNIX timestamp to IST using pytz
                utc_time = datetime.utcfromtimestamp(create_time).replace(tzinfo=pytz.utc)
                ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
                
                current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
                
                # Compare create_time with current time
                if (current_time - ist_time).seconds < 60 or state == "moving":
                    return "active"
    except requests.RequestException:
        return "inactive"

    return "inactive"

# Function to update robot data in a text file
def update_robot_data(robot_info):
    with open("/root/robot_data.txt", "w") as file:
        for robot in robot_info:
            file.write(f"Robot_SN: {robot['Robot_SN']}, Robot_IP: {robot['Robot_IP']}, Status: {robot['Status']}\n")

# Main function to execute the process
def main():
    local_ip = get_local_ip()
    base_ip = get_base_ip(local_ip)
    print(f"Scanning network: {base_ip}/24")

    ip_addresses = get_ip_addresses(base_ip)

    robot_info = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ip = {executor.submit(check_if_robot, ip): ip for ip in ip_addresses}

        for future in as_completed(future_to_ip):
            ip, sn = future.result()
            if sn:
                robot_info.append({
                    "Robot_SN": sn,
                    "Robot_IP": ip,
                    "Status": "unknown"
                })

    if robot_info:
        print("\nFound Robots:")
        for robot in robot_info:
            print(f"Robot_SN: {robot['Robot_SN']}, Robot_IP: {robot['Robot_IP']}")

        # Ping and check robot status in a loop
        while True:
            for robot in robot_info:
                status = check_robot_status(robot["Robot_IP"])
                robot["Status"] = status
                print(f"Robot_SN: {robot['Robot_SN']}, Robot_IP: {robot['Robot_IP']}, Status: {status}")
            
            # Update the robot data in the text file
            update_robot_data(robot_info)

            # Wait for 3 seconds before the next ping
            time.sleep(3)

    else:
        print("No robots found.")

if __name__ == "__main__":
    main()
