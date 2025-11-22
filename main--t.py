import websockets, asyncio, json


async def connect() -> None:
    ws_url: str = f"wss://ws.eulerstream.com?uniqueId=giovani94.1&apiKey=euler_ZTc1ZTUyOGNlZjVhNTk4NzJmOWQxMTlkZmY3ZWE4NDI5NTE5MzEwMzNmZWNiMTQ2NTI5YTc2"

    async with websockets.connect(ws_url) as websocket:
        async for message in websocket:
            data = json.loads(message)
            if "messages" in data:
                for msg in data["messages"]:
                    if msg["type"] in ["WebcastChatMessage","WebcastGiftMessage"]:
                        continue
                        if msg["type"] == "WebcastChatMessage":
                            print("Mensaje=> ")
                            print("Usuario: "+msg["data"]["user"]["nickname"]+"\nComentario: "+msg["data"]["comment"]+"\n\n")

                        if msg["type"] == "WebcastGiftMessage":
                            print("Regalo=> ")
                            print("Usuario: " + msg["data"]["user"]["nickname"]+str(msg["data"]["giftId"])+" Diamantes: "+str(msg["data"]["giftDetails"]["diamondCount"] )+ "\n")
                            print(msg["data"]["giftDetails"]["giftName"])# "Rose" 5655
                            print("\n")
                            print(msg)
                            print("\n\n")
                    else:
                        print(msg["type"])



asyncio.run(connect())