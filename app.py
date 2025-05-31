import asyncio
import binascii
import json
import random
from flask import Flask, request, jsonify
import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import uid_generator_pb2

app = Flask(__name__)

# Load 100 tokens from JSON file
def load_tokens():
    with open("token_ind.json", "r") as f:
        tokens = json.load(f)
    return random.sample(tokens, min(100, len(tokens)))  # 100 tokens select

# Create protobuf data
def create_protobuf(krishna, teamXdarks):
    message = uid_generator_pb2.uid_generator()
    message.krishna = krishna
    message.teamXdarks = teamXdarks
    return message.SerializeToString()

# Convert protobuf to hex
def protobuf_to_hex(protobuf_data):
    return binascii.hexlify(protobuf_data).decode()

# AES encrypt hex data
def encrypt_aes(hex_data):
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return binascii.hexlify(encrypted_data).decode()

# Async send one request
async def send_request(encrypted_uid, token, url):
    edata = bytes.fromhex(encrypted_uid)
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB48"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=edata, headers=headers) as response:
                await response.read()
                return response.status == 200
        except Exception as e:
            print(f"Request error: {e}")
            return False

# Async send 100 requests
async def send_multiple_requests(uid, tokens, url):
    krishna = int(uid)
    teamXdarks = 1
    protobuf_data = create_protobuf(krishna, teamXdarks)
    hex_data = protobuf_to_hex(protobuf_data)
    encrypted_uid = encrypt_aes(hex_data)

    tasks = [send_request(encrypted_uid, token["token"], url) for token in tokens]

    results = await asyncio.gather(*tasks)

    views_sent = sum(results)
    views_failed = len(results) - views_sent

    return views_sent, views_failed

# Async fetch player info from external API
async def fetch_player_info(uid):
    info_url = f"https://info-leader-krishna-api.vercel.app/profile_info?uid={uid}&region=ind"
    name = "Unknown"
    level = 0
    region_info = "IND"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as res:
                if res.status == 200:
                    data = await res.json()
                    if "AccountInfo" in data:
                        account_info = data["AccountInfo"]
                        name = account_info.get("AccountName", "Unknown")
                        level = account_info.get("AccountLevel", 0)
                        region_info = account_info.get("AccountRegion", region_info)
    except Exception as e:
        print(f"[ERROR] Failed to fetch player info: {e}")
    return name, level, region_info

# Flask endpoint
@app.route('/send_requests', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()

    if not uid or server_name != "IND":
        return jsonify({"error": "Only IND server is supported", "developer": "@teamXdarks"}), 400

    url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"

    selected_tokens = load_tokens()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    views_sent, views_failed = loop.run_until_complete(send_multiple_requests(uid, selected_tokens, url))
    name, level, region_info = loop.run_until_complete(fetch_player_info(uid))

    return jsonify({
        "Player Name": name,
        "UID": uid,
        "Region": region_info,
        "Level": level,
        "Views Sent": views_sent,
        "Views Failed": views_failed,
        "developer": "@teamXdarks"
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)