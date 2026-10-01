from typing import TYPE_CHECKING

from fastapi import FastAPI
from helpers.api_keygen import create_key
from helpers.auth import AuthenticatedUser, get_authenticated_user, SystemAuth
from helpers.models import PlaytimeEntry, PlaytimeResponse, UserModel
from helpers.ratelimiter import Duration, Limiter, Rate, RateLimiter
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

if TYPE_CHECKING:
    from js import Env

app = FastAPI(docs_url="/")

async def ratelimit_identifier(request: Request):
    user: AuthenticatedUser = await get_authenticated_user(request)
    return str(user.user_id)

@app.get("/init-db", dependencies=[SystemAuth], include_in_schema=False)
async def get_init_db(request: Request):
    env: "Env" = request.scope["env"]
    result = await env.PLAYTIME.prepare("CREATE TABLE IF NOT EXISTS api_keys (key TEXT, user_id TEXT)").run()
    result_2 = await env.PLAYTIME.prepare("CREATE TABLE IF NOT EXISTS playtime (user_id TEXT, start INTEGER, end INTEGER, type TEXT, map TEXT)").run()
    return {"message": "Database initialized", "data": [result, result_2]}

@app.get("/@me", dependencies=[RateLimiter(Limiter(Rate(5, Duration.MINUTE * 5)), identifier=ratelimit_identifier)])
async def get_authorized_user_info(request: Request, user: AuthenticatedUser) -> UserModel:
    return user

@app.post("/@me/playtime", dependencies=[RateLimiter(Limiter(Rate(5, Duration.MINUTE * 5)), identifier=ratelimit_identifier)], include_in_schema=False)
async def upload_playtime(request: Request, entries: list[PlaytimeEntry], user: AuthenticatedUser):
    if len(entries) > 100:
        return JSONResponse(status_code=400, content={"message": "Too many playtime entries"})
    env: "Env" = request.scope["env"]
    # do some sanity checks here:
    # - check if any of entries overlap or have invalid start/end times
    # - check if they overlap the range of what we already have saved in the database
    statement = await env.PLAYTIME.prepare("SELECT MIN(start) as min_start, MAX(end) as max_end FROM playtime WHERE user_id = ?").bind(str(user.user_id)).run()
    result = statement.results[0]
    min_start = result["min_start"]
    max_end = result["max_end"]
    for entry in entries:
        if entry.start >= entry.end:
            return JSONResponse(status_code=400, content={"message": "Invalid playtime entry: start time must be less than end time", "entry": entry.dict()})
        if min_start is not None and max_end is not None:
            if (entry.start < min_start and entry.end > min_start) or (entry.start < max_end and entry.end > max_end):
                return JSONResponse(status_code=400, content={"message": "Invalid playtime entry: overlaps with existing entries", "entry": entry.dict()})
    statement = env.PLAYTIME.prepare("INSERT INTO playtime (user_id, start, end, type, map) VALUES (?, ?, ?, ?, ?)")
    batch_result = await env.PLAYTIME.batch([
        statement.bind(str(user.user_id), entry.start, entry.end, entry.type, entry.map) for entry in entries
    ])
    return {"message": "OK"}

@app.get("/@me/playtime", dependencies=[RateLimiter(Limiter(Rate(5, Duration.MINUTE * 5)), identifier=ratelimit_identifier)])
async def get_my_playtime(request: Request, user: AuthenticatedUser) -> PlaytimeResponse:
    env: "Env" = request.scope["env"]
    result = (await env.PLAYTIME.prepare("SELECT * FROM playtime WHERE user_id = ?").bind(str(user.user_id)).run()).results
    return PlaytimeResponse(user_id=user.user_id, playtime=result)

@app.post("/{user_id}/keys", dependencies=[SystemAuth], include_in_schema=False)
async def create_api_key(request: Request, user_id: int):
    env: "Env" = request.scope["env"]
    new_key = create_key()
    # quickly verify it doesn't already exist (highly unlikely)
    result = True
    while result:
        new_key = create_key()
        result = (await env.PLAYTIME.prepare("SELECT * FROM api_keys WHERE key = ?").bind(new_key).run()).results
    await env.PLAYTIME.prepare("DELETE FROM api_keys WHERE user_id = ?").bind(str(user_id)).run()
    result = (await env.PLAYTIME.prepare("INSERT INTO api_keys (key, user_id) VALUES (?, ?)").bind(new_key, str(user_id)).run()).results
    return {"user_id": user_id, "key": new_key}

@app.get("/{user_id}/playtime", dependencies=[SystemAuth], include_in_schema=False)
async def get_user_playtime(request: Request, user_id: int) -> PlaytimeResponse:
    env: "Env" = request.scope["env"]
    result = (await env.PLAYTIME.prepare("SELECT * FROM playtime WHERE user_id = ?").bind(str(user_id)).run()).results
    return PlaytimeResponse(user_id=user_id, playtime=result)

from workers import asgi
Default = asgi.entrypoint(app)