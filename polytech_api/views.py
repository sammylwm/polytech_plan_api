from dmr import Controller, Query
from dmr.plugins.pydantic import PydanticSerializer

from .schemas import PingRequest, PingResponse


class PingController(Controller[PydanticSerializer]):
    async def get(self, parsed_query: Query[PingRequest]) -> PingResponse:
        return PingResponse()
