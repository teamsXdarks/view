import asyncio
import binascii
import json
import random
from flask import Flask, request, jsonify
import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import uid_generator_pb2  # Make sure compiled from your .proto file

app = Flask(__name__)

def load_tokens():
    with open("token_ind.json", "r") as f:
        tokens = json.load(f)
    return random.sample(tokens, min(100, len(tokens)))

def create_protobuf(krishna, teamXdarks):
    message = uid_generator_pb2.uid_generator()
    message.krishna = krishna
    message.teamXdarks = teamXdarks
    return message.SerializeToString()

def protobuf_to_hex(protobuf_data):
    return binascii.hexlify(protobuf_data).decode()

def encrypt_aes(hex_data):
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return binascii.hexlify(encrypted_data).decode()

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
        'ReleaseVersion': "OB49"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=edata, headers=headers) as response:
                await response.read()
                return response.status == 200
        except Exception as e:
            print(f"Request error: {e}")
            return False

async def send_multiple_requests(uid, tokens, url):
    krishna = int(uid)
    protobuf_data = create_protobuf(krishna, 1)
    encrypted_uid = encrypt_aes(protobuf_to_hex(protobuf_data))

    tasks = []
    for token in tokens:
        for _ in range(10):
            tasks.append(send_request(encrypted_uid, token["token"], url))

    results = await asyncio.gather(*tasks)
    return sum(results), len(results) - sum(results)

async def fetch_player_info(uid, server_name):
    info_url = f"https://info-silk.vercel.app/profile_info?uid={uid}&region={server_name.lower()}"
    name = "Unknown"
    level = 0
    region_info = server_name.upper()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as res:
                if res.status == 200:
                    try:
                        raw = await res.text()
                        data = json.loads(raw)
                        if "AccountInfo" in data:
                            acc = data["AccountInfo"]
                            name = acc.get("AccountName", name)
                            level = acc.get("AccountLevel", level)
                            region_info = acc.get("AccountRegion", region_info)
                    except Exception as json_err:
                        print(f"[JSON ERROR] {json_err}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch player info: {e}")

    return name, level, region_info

@app.route('/send_requests', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()

    if not uid or server_name != "IND":
        return jsonify({"error": "Only IND server is supported"}), 400

    url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    selected_tokens = load_tokens()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    views_sent, views_failed = loop.run_until_complete(send_multiple_requests(uid, selected_tokens, url))
    name, level, region = loop.run_until_complete(fetch_player_info(uid, server_name))

    return jsonify({        
         "UID": uid,
         "Player Name": name,
         "Level": level,
         "Region": region,
         "Views_Success": views_sent,
         "Views_Failed": views_failed,
         "Developer": "@teamXdarks",
}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5003)
