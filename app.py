from flask import Flask, jsonify
import aiohttp
import asyncio
import json
from byte import encrypt_api, Encrypt_ID

app = Flask(__name__)

def load_tokens(server_name):
    try:
        if server_name == "IND":
            path = "token_ind.json"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            path = "token_br.json"
        else:
            path = "token_bd.json"

        with open(path, "r") as f:
            data = json.load(f)

        tokens = [item["token"] for item in data if "token" in item and item["token"] not in ["", "N/A"]]
        return tokens
    except Exception as e:
        app.logger.error(f"❌ Token load error for {server_name}: {e}")
        return []

def get_url(server_name):
    if server_name == "IND":
        return "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        return "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
    else:
        return "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"

async def visit(session, url, token, uid, data):
    headers = {
        "ReleaseVersion": "OB49",
        "X-GA": "v1 1",
        "Authorization": f"Bearer {token}",
        "Host": url.replace("https://", "").split("/")[0]
    }
    try:
        async with session.post(url, headers=headers, data=data, ssl=False) as resp:
            if resp.status == 200:
                await resp.read()
                return True
            else:
                return False
    except:
        return False

async def send_until_200_success(tokens, uid, server_name, target_success=200):
    url = get_url(server_name)
    connector = aiohttp.TCPConnector(limit=0)
    total_success = 0
    total_sent = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        encrypted = encrypt_api("08" + Encrypt_ID(str(uid)) + "1801")
        data = bytes.fromhex(encrypted)

        while total_success < target_success:
            batch_size = min(target_success - total_success, 200)  # Send max 200 or remaining needed
            tasks = [
                asyncio.create_task(visit(session, url, tokens[(total_sent + i) % len(tokens)], uid, data))
                for i in range(batch_size)
            ]
            results = await asyncio.gather(*tasks)
            batch_success = sum(1 for r in results if r)
            total_success += batch_success
            total_sent += batch_size

            print(f"Batch sent: {batch_size}, Success in batch: {batch_success}, Total success so far: {total_success}")

    return total_success, total_sent

@app.route('/<string:server>/<int:uid>', methods=['GET'])
def send_visits(server, uid):
    server = server.upper()
    tokens = load_tokens(server)

    if not tokens:
        return jsonify({"message": "❌ No valid tokens found"}), 500

    print(f"🚀 Sending visits to UID: {uid} using {len(tokens)}")
    print("Waiting for total 200 successful visits...")

    total_success, total_sent = asyncio.run(send_until_200_success(
        tokens, uid, server,
        target_success=200
    ))

    return jsonify({
        "message": f"✅ Sent {total_success} successful visits in total."
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=50099)