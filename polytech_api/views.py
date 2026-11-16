from dmr import Controller, Query
from dmr.plugins.pydantic import PydanticSerializer
from parser.schedule import get_schedule_period

from .schemas import ScheduleRequest, ScheduleResponse


class ScheduleController(Controller[PydanticSerializer]):
    async def get(self, parsed_query: Query[ScheduleRequest]) -> ScheduleResponse:
        response = await get_schedule_period(
            parsed_query.group, parsed_query.start, parsed_query.end
        )
        return ScheduleResponse(root=response)
