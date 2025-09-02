import json
import hashlib
import getpass
import requests
import os

BASE_URL = "https://globalapi.solarmanpv.com"

def create_passhash(password: str) -> str:
    """Return SHA256 hash of password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_token(appid, secret, username, passhash):
    """Get bearer token from Solarman API."""
    url = f"{BASE_URL}/account/v1.0/token?appId={appid}&language=en"
    payload = {
        "appSecret": secret,
        "email": username,
        "password": passhash
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    data = r.json()

    # ✅ Fix: Accept success even if code is None
    if not data.get("access_token"):
        raise RuntimeError(f"Failed to get token: {data}")
    
    return data["access_token"]


def get_station_id(token):
    """Retrieve stationId from API."""
    url = f"{BASE_URL}/station/v1.0/list?language=en"
    headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json"}
    payload = {"size": 20, "page": 1}
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    data = r.json()
    station_list = data.get("stationList", [])
    if not station_list:
        raise RuntimeError("No stations found.")
    return station_list[0]["id"]

def get_device_id(token, station_id, device_type):
    """Retrieve device SN for inverter or collector."""
    url = f"{BASE_URL}/station/v1.0/device?language=en"
    headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json"}
    payload = {"size": 10, "page": 1, "stationId": station_id, "deviceType": device_type}
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    data = r.json()
    devices = data.get("deviceListItems", [])
    if not devices:
        raise RuntimeError(f"No devices found for {device_type}.")
    return devices[0]["deviceSn"]

def main():
    print("=== SolarmanPV Config Generator ===")

    # Get credentials from user
    name = input("Enter platform name (default: Trannergy): ") or "Trannergy"
    appid = input("Enter your APPID: ")
    secret = input("Enter your APPSECRET: ")
    username = input("Enter your username (email): ")
    password = getpass.getpass("Enter your password (will be hashed): ")
    passhash = create_passhash(password)

    # Get token
    print("Requesting access token...")
    token = get_token(appid, secret, username, passhash)

    print("Fetching stationId...")
    station_id = get_station_id(token)

    print("Fetching inverterId...")
    inverter_id = get_device_id(token, station_id, "INVERTER")

    print("Fetching loggerId...")
    logger_id = get_device_id(token, station_id, "COLLECTOR")

    # Optional meterId
    meter_id = input("Enter meterId (optional, press Enter to skip): ")
    meter_id = int(meter_id) if meter_id else None

    # MQTT settings
    broker = input("MQTT broker address [default: localhost]: ") or "localhost"
    port = input("MQTT port [default: 1883]: ")
    port = int(port) if port else 1883
    topic = input("MQTT topic [default: solarmanpv]: ") or "solarmanpv"
    mqtt_username = input("MQTT username (optional): ")
    mqtt_password = getpass.getpass("MQTT password (optional): ")

    # Build config
    config = {
        "name": name,
        "url": "globalapi.solarmanpv.com",
        "appid": appid,
        "secret": secret,
        "username": username,
        "passhash": passhash,
        "stationId": station_id,
        "inverterId": inverter_id,
        "loggerId": logger_id,
        "debug": False,
        "mqtt": {
            "broker": broker,
            "port": port,
            "topic": topic,
            "username": mqtt_username,
            "password": mqtt_password,
            "qos": 1,
            "retain": True
        }
    }
    if meter_id:
        config["meterId"] = meter_id

    # Write file
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Config file created successfully at {os.path.abspath('config.json')}")

if __name__ == "__main__":
    main()
