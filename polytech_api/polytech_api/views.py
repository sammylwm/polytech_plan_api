from http import HTTPStatus

from deadlines.models import Deadline, Group
from django.db.models import QuerySet
from django.http import JsonResponse
from dmr import APIError, Body, Controller, Query, ResponseSpec, modify, validate
from dmr.plugins.pydantic import PydanticSerializer
from parser.schedule import get_schedule_period

from .schemas import (
    DeadlineCreateRequest,
    DeadlineDeleteRequest,
    DeadlineItem,
    DeadlineRequest,
    DeadlineResponse,
    ScheduleRequest,
    ScheduleResponse,
)


def deadlines_for_period(query: ScheduleRequest) -> QuerySet[Deadline]:
    return Deadline.objects.filter(
        group__name=query.group,
        date__range=(query.start, query.end),
    ).order_by("date", "pk")


def deadline_item(deadline: Deadline, group: str) -> DeadlineItem:
    return DeadlineItem(
        id=deadline.pk,
        date=deadline.date,
        subject=deadline.subject,
        deadline=deadline.deadline,
        group=group,
    )


class ScheduleController(Controller[PydanticSerializer]):
    async def get(self, parsed_query: Query[ScheduleRequest]) -> ScheduleResponse:
        lessons = await get_schedule_period(
            parsed_query.group, parsed_query.start, parsed_query.end
        )
        deadlines = [
            deadline_item(deadline, parsed_query.group)
            async for deadline in deadlines_for_period(parsed_query)
        ]
        return ScheduleResponse(lessons=lessons, deadlines=deadlines)


class DeadlineContoller(Controller[PydanticSerializer]):
    def get(self, parsed_query: Query[DeadlineRequest]) -> DeadlineResponse:
        return DeadlineResponse(
            root=[
                deadline_item(deadline, parsed_query.group)
                for deadline in deadlines_for_period(parsed_query)
            ]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        extra_responses=[
            ResponseSpec(dict[str, str], status_code=HTTPStatus.CONFLICT),
        ],
    )
    def post(self, parsed_body: Body[DeadlineCreateRequest]) -> DeadlineItem:
        group, _ = Group.objects.get_or_create(name=parsed_body.group)
        deadline, created = Deadline.objects.get_or_create(
            date=parsed_body.date,
            subject=parsed_body.subject,
            deadline=parsed_body.deadline,
            group=group,
        )
        if created:
            return deadline_item(deadline, group.name)

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
