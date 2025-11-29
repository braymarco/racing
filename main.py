import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from starlette.responses import JSONResponse
from enum import Enum

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
start_pos = 50

finish_line = canvas_width - sprite_width - start_pos

all_cars = [
    "argentina", "bolivia", "brasil", "chile", "colombia", "costa_rica", "cuba",
    "ecuador", "el_salvador", "guatemala", "honduras", "mexico", "nicaragua",
    "panama", "paraguay", "peru", "uruguay", "usa", "venezuela"
]

VOTES_TO_QUALIFY = 5  # y votes
MAX_RACERS = 4        # x cars

# ============================
# ESTADO
# ============================
class GamePhase(str, Enum):
    VOTING = "VOTING"
    WAITING = "WAITING"
    COUNTDOWN = "COUNTDOWN"
    RACING = "RACING"
    FINISHED = "FINISHED"

class GameState:
    def __init__(self):
        self.phase = GamePhase.VOTING
        self.cars = {}  # { "argentina": { "pos": 25, "vel": 1 } }
        self.votes = {car: 0 for car in all_cars} # { "argentina": 0, ... }
        self.confirmed_cars = [] # ["argentina", "brasil"]
        self.winner = None

game_state = GameState()
clients = set()

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

async def broadcast_state():
    """Broadcasts the full current state to all clients"""
    state_msg = {
        "type": "state_update",
        "phase": game_state.phase,
        "cars": list(game_state.cars.keys()), # Only active cars
        "confirmed_cars": game_state.confirmed_cars,
        "votes": game_state.votes,
        "winner": game_state.winner
    }
    await broadcast(state_msg)


# ============================
# API
# ============================

@app.get("/vote/{car}")
async def vote_car(car: str):
    if game_state.phase != GamePhase.VOTING:
        return {"error": "Voting is closed"}

    if car not in all_cars:
        return {"error": f"Car {car} does not exist"}

    if car in game_state.confirmed_cars:
        return {"message": f"{car} is already confirmed"}

    game_state.votes[car] += 1

    # Check if qualified
    if game_state.votes[car] >= VOTES_TO_QUALIFY:
        if car not in game_state.confirmed_cars:
            game_state.confirmed_cars.append(car)
            # Add to cars dict for racing logic later
            game_state.cars[car] = {"pos": start_pos, "vel": 1}

            # Check if we have enough cars
            if len(game_state.confirmed_cars) >= MAX_RACERS:
                asyncio.create_task(start_sequence())

    await broadcast_state()
    return {"status": "voted", "votes": game_state.votes[car], "confirmed": car in game_state.confirmed_cars}

async def start_sequence():
    global game_state

    # Transition to WAITING
    game_state.phase = GamePhase.WAITING
    # Clear unconfirmed cars from votes/display logic implicitly by only sending confirmed_cars in state
    await broadcast_state()

    await asyncio.sleep(5)

    # Transition to COUNTDOWN
    game_state.phase = GamePhase.COUNTDOWN
    await broadcast_state()

    # Countdown 5, 4, 3, 2, 1
    for i in range(5, 0, -1):
        await broadcast({"type": "countdown", "value": i})
        await asyncio.sleep(1)

    await broadcast({"type": "countdown", "value": "GO!"})

    # Start Racing
    game_state.phase = GamePhase.RACING
    await broadcast_state()
    asyncio.create_task(race_loop())

@app.get("/hard_reset")
async def hard_reset():
    global game_state
    game_state = GameState()
    await broadcast_state()
    return {"status": "hard_reset"}

# Keep old reset for compatibility if needed, but alias to hard_reset or partial?
# The requirement says "clean the entire game and allow starting new voting".
@app.get("/reset")
async def reset():
    return await hard_reset()

# Serve static files (sprites)
app.mount("/sprites", StaticFiles(directory="sprites"), name="sprites")

# Serve index.html
@app.get("/")
async def get():
    return FileResponse("index.html")

# Serve admin panel
@app.get("/admin")
async def get_admin():
    return FileResponse("admin.html")

# ============================
# BUCLE DE LA CARRERA
# ============================
async def race_loop():
    while game_state.phase == GamePhase.RACING:
        await asyncio.sleep(0.05)  # 20 FPS

        # Actualizar física (Mover carros)
        for c in game_state.cars.values():
            # Aumentamos la velocidad base para que no sea tan lento
            #c["pos"] += c["vel"] + random.randint(1, 20) / 10
            c["vel"] = max(1, c["vel"] - 0.05)

        # Detectar ganador usando la PUNTA del carro
        current_positions = {}
        winner = None

        for name, c in game_state.cars.items():
            current_positions[name] = c["pos"]

            # CALCULO CLAVE: Posición del centro + mitad del largo = Nariz
            nose_position = c["pos"] + car_nose_offset

            if nose_position >= finish_line_x:
                winner = name
                break

        await broadcast({
            "type": "positions",
            "data": current_positions
        })

        if winner:
            game_state.phase = GamePhase.FINISHED
            game_state.winner = winner
            await broadcast({
                "type": "winner",
                "data": winner
            })
            await broadcast_state() # Ensure state reflects finished
            return  # Salir del loop

# ============================
# CONEXIÓN WS
# ============================
@app.websocket("/ws")
async def ws_connection(ws: WebSocket):
    await ws.accept()
    clients.add(ws)

    # Send initial state
    await ws.send_json({
        "type": "state_update",
        "phase": game_state.phase,
        "cars": list(game_state.cars.keys()),
        "confirmed_cars": game_state.confirmed_cars,
        "votes": game_state.votes,
        "winner": game_state.winner
    })

    try:
        while True:
            await ws.receive_text()
    except:
        clients.remove(ws)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
