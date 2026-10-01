from pydantic import BaseModel

class PlaytimeEntry(BaseModel):
    start: int
    end: int
    type: str
    map: str

class PlaytimeResponse(BaseModel):
    user_id: int
    playtime: list[PlaytimeEntry]


class UserModel(BaseModel):
    user_id: int