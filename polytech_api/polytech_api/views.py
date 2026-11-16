from http import HTTPStatus

from deadlines.models import Deadline, Group
from django.http import JsonResponse
from dmr import APIError, Body, Controller, Query, ResponseSpec, modify, validate
from dmr.plugins.pydantic import PydanticSerializer
from parser.schedule import get_schedule_period

from .schemas import (
    DeadlineDeleteRequest,
    DeadlineRequest,
    DeadlineResponse,
    ScheduleRequest,
    ScheduleResponse,
)


class ScheduleController(Controller[PydanticSerializer]):
    async def get(self, parsed_query: Query[ScheduleRequest]) -> ScheduleResponse:
        response = await get_schedule_period(
            parsed_query.group, parsed_query.start, parsed_query.end
        )
        return ScheduleResponse(root=response)


class DeadlineContoller(Controller[PydanticSerializer]):
    @modify(
        status_code=HTTPStatus.CREATED,
        extra_responses=[
            ResponseSpec(dict[str, str], status_code=HTTPStatus.CONFLICT),
        ],
    )
    def post(
        self, parsed_body: Body[DeadlineRequest]
    ) -> DeadlineResponse:
        group, _ = Group.objects.get_or_create(name=parsed_body.group)
        deadline, created = Deadline.objects.get_or_create(
            date=parsed_body.date,
            subject=parsed_body.subject,
            deadline=parsed_body.deadline,
            group=group,
        )
        if created:
            return DeadlineResponse(
                id=deadline.pk,
                date=deadline.date,
                subject=deadline.subject,
                deadline=deadline.deadline,
                group=group.name,
            )

        raise APIError(
            {"detail": "Такая запись уже существует"},
            status_code=HTTPStatus.CONFLICT,
        )

    @validate(
        ResponseSpec(dict[str, str], status_code=HTTPStatus.OK),
        ResponseSpec(dict[str, str], status_code=HTTPStatus.NOT_FOUND),
    )
    def delete(self, parsed_query: Query[DeadlineDeleteRequest]) -> JsonResponse:
        deleted, _ = Deadline.objects.filter(id=parsed_query.id).delete()

        if not deleted:
            return JsonResponse({"detail": "Запись не найдена"}, status=404)
        return JsonResponse({"detail": "Запись удалена"})
