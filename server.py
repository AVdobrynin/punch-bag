import json
import asyncio
import threading
import sys
import websockets

from hx711_weight import HX711

event = threading.Event()
started = False
hxs = [HX711(5, 6), HX711(14, 15), HX711(17, 27), HX711(18, 19), HX711(22, 25), HX711(23, 24), HX711(26, 16), HX711(4, 3)]
hxs_ratio = [-0.77045, -0.7108, -0.7042, -0.7194, -0.69965, -0.716, -0.6916, -0.72945]
hx_val = [0, 0, 0, 0, 0, 0, 0, 0]
hx_initialized = [0, 0, 0, 0, 0, 0, 0, 0]


def hx_init_start():
    """
    hx_init_start используется для инициализации микросхем hx711. указывает на то, 
    что этот код предназначен для выполнения некоторых начальных действий 
    перед использованием HX711. Он выполняет несколько шагов:

    Сброс HX711 – Этот шаг обнуляет состояние микросхемы до заводских настроек.
    Установка коэффициента усиления для канала A равным 64 – Это значение может 
    быть установлено разработчиком в зависимости от требуемого уровня сигнала.
    Выбор канала ‘A’ – В данном случае канал A выбран для использования.
    Чтение данных 10 раз – Это позволяет убедиться, что все данные получены 
    правильно и микросхема работает должным образом.
    Обнуление HX711 – Этот шаг возвращает микросхему в исходное состояние, 
    чтобы можно было начать новый цикл измерений.
    Повторное чтение данных 10 раз – Еще одно подтверждение того, что все данные были успешно считаны.
    """
    
    for hx in hxs:
        hx.reset()
        hx.set_gain_A(gain=64)  # You can change the gain for channel A  at any time.
        hx.select_channel(channel='A')  # Select desired channel. Either 'A' or 'B' at any time.
        data = hx.get_data_mean(readings=10)
        result = hx.zero(readings=10)
        data = hx.get_data_mean(readings=10)


# def calibrate_hx(known_weight_grams: float):
#     known_weight_grams = known_weight_grams * 1000
#     data = hx.get_data_mean(readings=30)
#     ratio = data / known_weight_grams
#     hx.set_scale_ratio(ratio)

def calibrate_hx(hx, ratio):
    """
    Метод calibrate_hx используется для калибровки соотношения для конкретного чипа HX711. 
    Вы можете использовать известный вес для расчета этого соотношения. После этого вы можете 
    использовать этот метод для калибровки чипа HX711.

    Аргументы:

    hx: экземпляр класса HX711
    ratio: соотношение для расчёта веса в желаемых единицах
    """
    hx.set_scale_ratio(ratio)

def get_hx_data(hx):
    try:
        val = hx.get_weight_mean(1)
        if val < 0:
            val = val * (-1)
    except Exception:
        return 0
    return val / 1000
        
        
async def ws_sender(ws, hxs) -> None:
    """
    Метод `ws_sender` является вспомогательной функцией для отправки данных о весе 
    подключенным клиентам вебсокетов.

    Он запускает бесконечный цикл, который отправляет текущие данные о весе всем 
    подключенным клиентам вебсокетов каждый раз, когда событие устанавливается. 
    Если событие не установлено, он отправляет сообщение со всеми весами, установленными 
    на ноль, всем подключенным клиентам вебсокетов.

    Параметры:
    - `ws`: объект соединения WebSocketServerProtocol.
    - `hxs`: список объектов HX711.

    Возвращаемое значение:
    - `None`.
    """
    try:
        print(f"event: {event.is_set()}")
        while True:
            if event.is_set():
                for i in range(0, 8):
                    val = round(get_hx_data(hxs[i]), 2)
                    sys.stdout.write("num is: %d. Val progress: %d%%   \r"% (i, val) )
                    if val > 10 and val > hx_val[i] and val <= 2000:
                        hx_val[i] = val
                        print(hx_val)
                        await ws.send(json.dumps({"message": "load", "data": hx_val}))
                sys.stdout.flush()
            else:
                 for i in range(0, 8):
                    hx_val[i] = 0 
            # if val is not None:
            #     await ws.send(json.dumps({"message": "load", "data": val}))
    except Exception:
        return


def loop_in_thread(loop, ws, hxs):
    """
    Метод `loop_in_thread` является вспомогательной функцией для запуска цикла 
    событий asyncio и задачи `ws_sender` в отдельном потоке.

    Параметры:
    - `loop`: asyncio.AbstractEventLoop, цикл событий asyncio для использования.
    - `ws`: объект подключения WebSocketServerProtocol.
    - `hxs`: список объектов HX711.

    Возвращаемое значение:
    - `None`.
    """
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_sender(ws, hxs))


async def handler(websocket):
    """
    Handler – это обработчик вебсокетов asyncio, который обрабатывает входящие сообщения.

    Handler будет получать сообщения от подключенного клиента вебсокета и обрабатывать их 
    соответствующим образом. Он отправит клиенту статусное сообщение с информацией об 
    инициализации и статусе начала работы микросхем HX711. Если клиент отправляет команду 
    инициализации, он калибрует микросхему HX711 на указанной позиции с заданным соотношением. 
    Если клиент отправляет команду старта, он запустит цикл событий asyncio и задачу ws_sender 
    в отдельном потоке, если они еще не запущены. Если клиент отправляет команду остановки, 
    он остановит цикл событий asyncio и задачу ws_sender в отдельном потоке.
    """
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
                        loop = asyncio.new_event_loop()
                        t = threading.Thread(target=loop_in_thread, args=(loop,websocket, hxs))
                        t.start()  
            elif message["message"] == "stop":
                event.clear()
                await websocket.send(json.dumps({"message": "stopped"}))
                for i in range(0, 8):
                    hx_val[i] = 0 

        except Exception as e:
            raise e from e
            print("CLOSED")
            await websocket.close()

async def main():
    """
    Main – это главная точка входа asyncio для этого скрипта. Она начинает цикл событий 
    asyncio и сервер вебсокетов на порте 8000. Затем она бесконечно запускает сервер 
    вебсокетов до тех пор, пока не будет завершена работа скрипта.

    Параметры:
    - `None`.

    Возвращаемое значение:
    - `None`.
    """
    async with websockets.serve(handler, "", 8000):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    event.clear()
    hx_init_start()
    print("SERVER STARTED")
    asyncio.run(main())