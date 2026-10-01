import secrets
from typing import Annotated, TYPE_CHECKING

from fastapi import Depends, HTTPException
from helpers.models import UserModel
from pydantic import BaseModel
from starlette.requests import Request


if TYPE_CHECKING:
    from js import Env


async def get_authenticated_user(request: Request) -> UserModel:
    env: "Env" = request.scope["env"]
    key = request.headers.get("Authorization")
    if key is None:
        raise HTTPException(401, "Unauthorized")
    # verify session token is valid
    result = await env.PLAYTIME.prepare("SELECT user_id FROM api_keys WHERE key = ?").bind(key).run()
    user_id = result.results[0]["user_id"] if result.results else None
    if not user_id:
        raise HTTPException(401, "Unauthorized")
    return UserModel(user_id=int(user_id))

AuthenticatedUser = Annotated[UserModel, Depends(get_authenticated_user)]

def system_auth() -> Depends:
    async def wrapped(request: Request) -> None:
        env: "Env" = request.scope["env"]
        key = request.headers.get("Authorization")
        if key is None or not secrets.compare_digest(key, env.SYSTEM_API_KEY):
            raise HTTPException(401, "Unauthorized")
        return None

    return Depends(wrapped)

SystemAuth = system_auth()