from typing import Literal

from pydantic import BaseModel


class PingRequest(BaseModel):
    message: Literal["ping"] = "ping"


class PingResponse(BaseModel):
    message: Literal["pong"] = "pong"
