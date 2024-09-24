

import json
import asyncio
import threading

import websockets

from hx711_weight import HX711

event = threading.Event()
started = False
hxs = [HX711(5, 6), HX711(14, 15), HX711(17, 27), HX711(18, 19), HX711(22, 25), HX711(23, 24), HX711(26, 16), HX711(4, 3)]
hxs_ratio = [-0.77045, -0.7108, -0.7042, -0.7194, -0.69965, -0.716, -0.6916, -0.72945]
hx_val = [0, 0, 0, 0, 0, 0, 0, 0]
hx_initialized = [0, 0, 0, 0, 0, 0, 0, 0]
hx_loop = [0, 0, 0, 0, 0, 0, 0, 0]


def hx_init_start():
    for hx in hxs:
        hx.reset()
        hx.set_gain_A(gain=64)  # You can change the gain for channel A  at any time.
        hx.select_channel(channel='A')  # Select desired channel. Either 'A' or 'B' at any time.
        data = hx.get_data_mean(readings=30)
        result = hx.zero(readings=30)
        data = hx.get_data_mean(readings=30)


# def calibrate_hx(known_weight_grams: float):
#     known_weight_grams = known_weight_grams * 1000
#     data = hx.get_data_mean(readings=30)
#     ratio = data / known_weight_grams
#     hx.set_scale_ratio(ratio)

def calibrate_hx(hx, ratio):
    hx.set_scale_ratio(ratio)

def get_hx_data(hx):
    try:
        val = hx.get_weight_mean(1)
        if val < 0:
            val = val * (-1)

    except Exception:
        return 0
    return val / 1000
        
        
async def ws_sender(ws, hxs, elem) -> None:
    try:
        print(f"event: {event.is_set()}, elem:{elem}")
        while True:
            if event.is_set():
                val = round(get_hx_data(hxs[elem]), 2)
                if val > 100 and val > hx_val[elem] and val <= 2000:
                    hx_val[elem] = val
                    print(hx_val)
                    await ws.send(json.dumps({"message": "load", "data": hx_val}))
            else:
                hx_val[elem] = 0
            # if val is not None:
            #     await ws.send(json.dumps({"message": "load", "data": val}))
    except Exception:
        return


def loop_in_thread(loop, ws, hxs, elem):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_sender(ws, hxs, elem))


async def handler(websocket):
    async for msg in websocket:
        try:
            message = json.loads(msg)
            if message["message"] == "status":
                await websocket.send(json.dumps({"message": "status", "data": { "initialized": hx_initialized, "started": event.is_set()}}))
            elif message["message"] == "initialize":
                calibrate_hx(hxs[message["id"]], hxs_ratio[message["id"]])
                await websocket.send(json.dumps({"message": "initialized", "id":message["id"]}))
            elif message["message"] == "start":
                print("START")
                await websocket.send(json.dumps({"message": "started"}))
                if(not event.is_set()):
                    print("prepare")
                    if(not started):
                        print("loop")
                        event.set()
                        for i in range(0, len(hx_loop)):
                            print(f"loop #: {i}")
                            threading.Thread(target=loop_in_thread, args=(asyncio.new_event_loop(),websocket, hxs, i)).start()    
            elif message["message"] == "stop":
                event.clear()
                hx_val = [0, 0, 0, 0, 0, 0, 0, 0]
                await websocket.send(json.dumps({"message": "stopped"}))

        except Exception as e:
            raise e from e
            print("CLOSED")
            await websocket.close()

async def main():
    async with websockets.serve(handler, "", 8000):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    event.clear()
    hx_init_start()
    print("SERVER STARTED")
    asyncio.run(main())
