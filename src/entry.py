from fastapi import FastAPI
from helpers.api_keygen import create_key
from helpers.auth import AuthenticatedUser, SystemAuth
from helpers.models import PlaytimeEntry
from starlette.requests import Request
from starlette.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def get_index():
    # initialize
    return JSONResponse(content={"playtime": True})

@app.get("/init-db", dependencies=[SystemAuth])
async def get_init_db(request: Request):
    env = request.scope["env"]
    result = await env.PLAYTIME.prepare("CREATE TABLE IF NOT EXISTS api_keys (key TEXT, user_id INTEGER)").run()
    result_2 = await env.PLAYTIME.prepare("CREATE TABLE IF NOT EXISTS playtime (user_id INTEGER, start INTEGER, end INTEGER, type TEXT, mode TEXT)").run()
    return {"message": "Database initialized", "data": [result, result_2]}

@app.get("/@me")
async def get_authorized_user_info(request: Request, user: AuthenticatedUser):
    return user

@app.post("/@me/playtime")
async def upload_playtime(request: Request, entries: list[PlaytimeEntry], user: AuthenticatedUser):
    env = request.scope["env"]
    statement = env.PLAYTIME.prepare("INSERT INTO playtime (user_id, start, end, type, mode) VALUES (?, ?, ?, ?, ?)")
    batch_result = await env.PLAYTIME.batch([
        statement.bind(user.user_id, entry.start, entry.end, entry.type, entry.mode) for entry in entries
    ])
    return {"message": "Playtime data received", "data": batch_result}

@app.get("/@me/playtime")
async def get_my_playtime(request: Request, user: AuthenticatedUser):
    env = request.scope["env"]
    result = (await env.PLAYTIME.prepare("SELECT * FROM playtime WHERE user_id = ?").bind(user.user_id).run()).results # database stuff
    return {"user_id": user.user_id, "playtime": result}

@app.post("/{user_id}/keys", dependencies=[SystemAuth])
async def create_api_key(request: Request, user_id: int):
    env = request.scope["env"]
    new_key = create_key()
    # quickly verify it doesn't already exist (highly unlikely)
    result = True
    while result:
        new_key = create_key()
        result = (await env.PLAYTIME.prepare("SELECT * FROM api_keys WHERE key = ?").bind(new_key).run()).results
    result = (await env.PLAYTIME.prepare("INSERT INTO api_keys (key, user_id) VALUES (?, ?)").bind(new_key, user_id).run()).results # database stuff
    return {"user_id": user_id, "key": new_key}

@app.get("/{user_id}/playtime", dependencies=[SystemAuth])
async def get_user_playtime(request: Request, user_id: int):
    env = request.scope["env"]
    result = (await env.PLAYTIME.prepare("SELECT * FROM playtime WHERE user_id = ?").bind(user_id).run()).results # database stuff
    return {"user_id": user_id, "playtime": result}

from workers import asgi
Default = asgi.entrypoint(app)