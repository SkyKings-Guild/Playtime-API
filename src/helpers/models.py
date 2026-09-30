from pydantic import BaseModel

class PlaytimeEntry(BaseModel):
    start: int
    end: int
    type: str
    map: str
