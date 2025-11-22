import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from starlette.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ============================
# CONFIGURACIÓN
# ============================
canvas_width = 1280
sprite_width = 50
start_pos = 50             # <--- CAMBIO AQUÍ (Antes era 25)
                           # 70px asegura que la cola del auto (45px) entre sobrada.

# meta calculada o fija

finish_line = canvas_width - sprite_width - start_pos

all_cars = [
    "argentina", "bolivia", "brasil", "chile", "colombia", "costa_rica", "cuba",
    "ecuador", "el_salvador", "guatemala", "honduras", "mexico", "nicaragua",
    "panama", "paraguay", "peru", "uruguay", "usa", "venezuela"
]

# ============================
# ESTADO
# ============================
cars = {}  # { "argentina": { "pos": 25, "vel": 1 } }
clients = set()
race_running = False

# ============================
# CONSTANTES FÍSICAS
# ============================
finish_line_x = 1150  # Coordenada X visual de la línea de meta
car_length = 90       # Largo visual aproximado del carro en px
car_nose_offset = car_length / 2  # Distancia del centro a la punta
# ============================
# WEBSOCKET BROADCAST
# ============================
async def broadcast(message: dict):
    """Envía mensajes a todos los clientes conectados"""
    dead = []
    for ws in clients:
        try:
            await ws.send_json(message)
        except:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)


# ============================
# API: AGREGAR CARRO
# ============================
@app.get("/add_car/{car}")
async def add_car(car: str):
    global cars, race_running

    # Si intentan agregar un carro mientras corren, reiniciamos lógica (opcional)
    if race_running:
        return {"error": "La carrera ya está en curso"}

    if car not in all_cars:
        return {"error": f"El carro {car} no existe en la lista de assets"}

    if car in cars:
        return {"error": f"{car} ya está en la pista"}

    # Agregar carro
    cars[car] = {"pos": start_pos, "vel": 1}

    # AVISAR AL FRONTEND INMEDIATAMENTE
    await broadcast({
        "type": "players_update",
        "data": list(cars.keys())
    })

    return {
        "status": "added",
        "cars": list(cars.keys())
    }


@app.get("/start")
async def start():
    global race_running
    if len(cars) < 2:  # Mínimo 2 para que sea divertido
        return {"error": "Se necesitan al menos 2 carros"}

    race_running = True
    asyncio.create_task(race_loop())
    return {"status": "started"}


@app.get("/reset")
async def reset():
    global cars, race_running
    cars = {}
    race_running = False
    # Avisar al front que limpie la pantalla
    await broadcast({"type": "players_update", "data": []})
    return {"status": "reset"}


# ============================
# BUCLE DE LA CARRERA
# ============================
async def race_loop():
    global race_running

    while race_running:
        await asyncio.sleep(0.05)  # 20 FPS

        # Actualizar física (Mover carros)
        for c in cars.values():
            # Aumentamos la velocidad base para que no sea tan lento
            c["pos"] += c["vel"] + random.randint(1, 20) / 10
            c["vel"] = max(1, c["vel"] - 0.05)

        # Detectar ganador usando la PUNTA del carro
        current_positions = {}
        winner = None

        for name, c in cars.items():
            current_positions[name] = c["pos"]

            # CALCULO CLAVE: Posición del centro + mitad del largo = Nariz
            nose_position = c["pos"] + car_nose_offset

            if nose_position >= finish_line_x:
                winner = name
                # Detenemos aquí para que gane el que cruzó primero en este frame
                break

                # Enviar actualización
        await broadcast({
            "type": "positions",
            "data": current_positions
        })

        if winner:
            race_running = False
            await broadcast({
                "type": "winner",
                "data": winner
            })
            return  # Salir del loop

@app.get("/reset_car/{car_name}")
async def reset_single_car(car_name: str):

    if car_name not in cars:
        return JSONResponse(
            {"status": "error", "message": "Car does not exist"},
            status_code=404
        )

    # Reiniciar valores
    cars[car_name]["pos"] = start_pos
    cars[car_name]["vel"] = 5
    cars[car_name]["nitro"] = False

    # Notificar al frontend
    await broadcast({
        "type": "reset_car",
        "car": car_name
    })

    return {"status": "ok", "message": f"Car '{car_name}' reset"}
# ============================
# CONEXIÓN WS
# ============================
@app.websocket("/ws")
async def ws_connection(ws: WebSocket):
    await ws.accept()
    clients.add(ws)

    # Al conectar, enviar el estado actual por si ya había carros
    await ws.send_json({
        "type": "players_update",
        "data": list(cars.keys())
    })

    try:
        while True:
            await ws.receive_text()
    except:
        clients.remove(ws)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)