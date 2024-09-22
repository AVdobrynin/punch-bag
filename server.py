#import asyncio
#import websockets
# create handler for each connection
#async def handler(websocket, path):
 #   async for message in websocket:
    #    print(message)
   #     

#start_server = websockets.serve(handler, "0.0.0.0", 8000)

#asyncio.get_event_loop().run_until_complete(start_server)
#asyncio.get_event_loop().run_forever()


import json
import asyncio
import threading

import websockets

from hx711_weight import HX711


hx = HX711()


def hx_init_start():
    hx.reset()
    hx.set_gain_A(gain=64)  # You can change the gain for channel A  at any time.
    hx.select_channel(channel='A')  # Select desired channel. Either 'A' or 'B' at any time.
    data = hx.get_data_mean(readings=30)
    result = hx.zero(readings=30)
    data = hx.get_data_mean(readings=30)


def calibrate_hx(known_weight_grams: float):
    known_weight_grams = known_weight_grams * 1000
    data = hx.get_data_mean(readings=30)
    ratio = data / known_weight_grams
    hx.set_scale_ratio(ratio)


def get_hx_data():
    try:
        val = hx.get_weight_mean(1)
        if val < 0:
            val = val * (-1)
        print(val)
    except Exception:
        return 0
    return val / 1000
        
        
async def ws_sender(ws) -> None:
    try:
        while True:
            val = get_hx_data()
            if val is not None:
                await ws.send(json.dumps({"message": "load", "data": val}))
    except Exception:
        return


def loop_in_thread(loop, ws):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_sender(ws))


async def handler(websocket):
    async for msg in websocket:
        try:
            message = json.loads(msg)
            if message["message"] == "calibrate_start":
                print("START CALIBRATE")
                await websocket.send(json.dumps({"message": "Start calibrating"}))
                hx_init_start()
                await websocket.send(json.dumps({"message": "Put a known weight on device"}))
            elif message["message"] == "calibrate_weight":
                print("END CALIBRATE")
                calibrate_hx(float(message["data"]))
                await websocket.send(json.dumps({"message": "Device is calibrated"}))
            elif message["message"] == "start":
                print("START")
                loop = asyncio.new_event_loop()
                t = threading.Thread(target=loop_in_thread, args=(loop,websocket))
                t.start()

        except Exception as e:
            raise e from e
            print("CLOSED")
            await websocket.close()

async def main():
    async with websockets.serve(handler, "", 8000):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    print("SERVER STARTED")
    asyncio.run(main())
