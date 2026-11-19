from datetime import datetime
from http import HTTPStatus
from itertools import groupby
from operator import attrgetter
from typing import Annotated
from uuid import UUID

from deadlines.ai import (
    DeadlineAIError,
    DeadlineClarificationRequired,
    parse_homework,
    parse_session_tasks,
)
from deadlines.attachments import attachment_transaction, attachment_uploads
from deadlines.models import Deadline, DeadlineAttachment, Group, SessionTask
from deadlines.services import confirm_deadline
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_safe
from dmr import APIError, Body, Controller, Query, ResponseSpec, modify, validate
from dmr.negotiation import ContentType, conditional_type
from dmr.parsers import JsonParser, MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from parser.schedule import get_schedule_period

from .schemas import (
    AttachmentItem,
    DeadlineConfirmForm,
    DeadlineConfirmRequest,
    DeadlineConfirmResponse,
    DeadlineCreateForm,
    DeadlineCreateRequest,
    DeadlineDeleteRequest,
    DeadlineItem,
    DeadlineParseRequest,
    DeadlinePreview,
    DeadlineRequest,
    DeadlineResponse,
    ScheduleRequest,
    ScheduleResponse,
    SessionSubjectItem,
    SessionTaskCreateRequest,
    SessionTaskItem,
    SessionTaskRequest,
    SessionTaskResponse,
    SessionTaskTextRequest,
)


DeadlineCreateBody = Annotated[
    DeadlineCreateRequest,
    conditional_type(
        {
            ContentType.json: DeadlineCreateRequest,
            ContentType.multipart_form_data: DeadlineCreateForm,
        }
    ),
]
DeadlineConfirmBody = Annotated[
    DeadlineConfirmRequest,
    conditional_type(
        {
            ContentType.json: DeadlineConfirmRequest,
            ContentType.multipart_form_data: DeadlineConfirmForm,
        }
    ),
]


def deadlines_for_period(query: ScheduleRequest) -> QuerySet[Deadline]:
    return (
        Deadline.objects.filter(
            group__name=query.group,
            date__range=(query.start, query.end),
        )
        .prefetch_related("attachments")
        .order_by("date", "pk")
    )


def deadline_item(request: HttpRequest, deadline: Deadline, group: str) -> DeadlineItem:
    attachments = []
    for attachment in deadline.attachments.all():
        path = reverse("deadline-attachment", args=[attachment.pk])
        url = (
            f"{settings.PUBLIC_API_URL}{path}"
            if settings.PUBLIC_API_URL
            else request.build_absolute_uri(path)
        )
        attachments.append(
            AttachmentItem(name=attachment.name, size=attachment.size, url=url)
        )

    return DeadlineItem(
        id=deadline.pk,
        date=deadline.date,
        subject=deadline.subject,
        deadline=deadline.deadline,
        group=group,
        attachments=attachments,
    )


class ScheduleController(Controller[PydanticSerializer]):
    async def get(self, parsed_query: Query[ScheduleRequest]) -> ScheduleResponse:
        lessons = await get_schedule_period(
            parsed_query.group, parsed_query.start, parsed_query.end
        )
        deadlines = [
            deadline_item(self.request, deadline, parsed_query.group)
            async for deadline in deadlines_for_period(parsed_query)
        ]
        return ScheduleResponse(lessons=lessons, deadlines=deadlines)


@require_safe
def download_attachment(request: HttpRequest, attachment_id: UUID) -> FileResponse:
    attachment = get_object_or_404(DeadlineAttachment, pk=attachment_id)
    try:
        file = attachment.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("Файл не найден") from exc
    response = FileResponse(file, as_attachment=True, filename=attachment.name)
    response["X-Content-Type-Options"] = "nosniff"
    return response


class DeadlineContoller(Controller[PydanticSerializer]):
    parsers = (JsonParser(), MultiPartParser())

    def get(self, parsed_query: Query[DeadlineRequest]) -> DeadlineResponse:
        return DeadlineResponse(
            root=[
                deadline_item(self.request, deadline, parsed_query.group)
                for deadline in deadlines_for_period(parsed_query)
            ]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        extra_responses=[
            ResponseSpec(dict[str, str], status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.UNPROCESSABLE_ENTITY),
        ],
    )
    def post(self, parsed_body: Body[DeadlineCreateBody]) -> DeadlineItem:
        uploads = attachment_uploads(self.request)
        with attachment_transaction(uploads) as save_attachments:
            group, _ = Group.objects.select_for_update().get_or_create(
                name=parsed_body.group
            )
            deadline, created = Deadline.objects.get_or_create(
                date=parsed_body.date,
                subject=parsed_body.subject,
                deadline=parsed_body.deadline,
                group=group,
            )
            if not created:
                raise APIError(
                    {"detail": "Такая запись уже существует"},
                    status_code=HTTPStatus.CONFLICT,
                )
            save_attachments(deadline)
            return deadline_item(self.request, deadline, group.name)

    @validate(
        ResponseSpec(dict[str, str], status_code=HTTPStatus.OK),
        ResponseSpec(dict[str, str], status_code=HTTPStatus.NOT_FOUND),
    )
    def delete(self, parsed_query: Query[DeadlineDeleteRequest]) -> JsonResponse:
        deleted, _ = Deadline.objects.filter(id=parsed_query.id).delete()

        if not deleted:
            return JsonResponse({"detail": "Запись не найдена"}, status=404)
        return JsonResponse({"detail": "Запись удалена"})


def session_task_item(task: SessionTask, group: str) -> SessionTaskItem:
    return SessionTaskItem(
        id=task.pk,
        group=group,
        semester=task.semester,
        subject=task.subject,
        text=task.text,
        due_date=task.due_date,
    )


def session_subject_item(
    subject: str, tasks: list[SessionTaskItem]
) -> SessionSubjectItem:
    return SessionSubjectItem(
        subject=subject,
        text="\n".join(f"{number}. {task.text}" for number, task in enumerate(tasks, 1)),
        tasks=tasks,
    )


class SessionTaskController(Controller[PydanticSerializer]):
    parsers = (JsonParser(),)

    def get(self, parsed_query: Query[SessionTaskRequest]) -> SessionTaskResponse:
        tasks = SessionTask.objects.filter(
            group__name=parsed_query.group,
            semester=parsed_query.semester,
        ).order_by("subject", "pk")
        return SessionTaskResponse(
            root=[
                session_subject_item(
                    subject, [session_task_item(task, parsed_query.group) for task in items]
                )
                for subject, items in groupby(tasks, key=attrgetter("subject"))
            ]
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        extra_responses=[
            ResponseSpec(dict[str, str], status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.UNPROCESSABLE_ENTITY),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.SERVICE_UNAVAILABLE),
        ],
    )
    def post(
        self, parsed_body: Body[SessionTaskCreateRequest | SessionTaskTextRequest]
    ) -> SessionTaskItem | SessionSubjectItem:
        if isinstance(parsed_body, SessionTaskTextRequest):
            return self.add_from_text(parsed_body)

        with transaction.atomic():
            group, _ = Group.objects.select_for_update().get_or_create(
                name=parsed_body.group
            )
            task, created = SessionTask.objects.get_or_create(
                group=group,
                semester=parsed_body.semester,
                subject=parsed_body.subject,
                text=parsed_body.text,
                due_date=parsed_body.due_date,
            )
            if not created:
                raise APIError(
                    {"detail": "Такая запись уже существует"},
                    status_code=HTTPStatus.CONFLICT,
                )
        return session_task_item(task, parsed_body.group)

    def add_from_text(self, request: SessionTaskTextRequest) -> SessionSubjectItem:
        existing_subjects = list(
            SessionTask.objects.filter(
                group__name=request.group, semester=request.semester
            ).order_by("subject").values_list("subject", flat=True).distinct()
        )
        try:
            parsed = parse_session_tasks(request.text, request.group, existing_subjects)
        except DeadlineClarificationRequired as exc:
            raise APIError(
                {"detail": str(exc)}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY
            ) from exc
        except DeadlineAIError as exc:
            raise APIError(
                {"detail": "Не удалось обработать задания через ИИ. Попробуй позже."},
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            ) from exc

        with transaction.atomic():
            group, _ = Group.objects.select_for_update().get_or_create(name=request.group)
            tasks = SessionTask.objects.filter(
                group=group, semester=request.semester, subject=parsed.subject
            )
            for item in parsed.tasks:
                tasks.get_or_create(
                    group=group,
                    semester=request.semester,
                    subject=parsed.subject,
                    text=item.text,
                    due_date=item.due_date,
                )
            return session_subject_item(
                parsed.subject,
                [session_task_item(task, request.group) for task in tasks.order_by("pk")],
            )

    @validate(
        ResponseSpec(dict[str, str], status_code=HTTPStatus.OK),
        ResponseSpec(dict[str, str], status_code=HTTPStatus.NOT_FOUND),
    )
    def delete(self, parsed_query: Query[DeadlineDeleteRequest]) -> JsonResponse:
        deleted, _ = SessionTask.objects.filter(pk=parsed_query.id).delete()
        if not deleted:
            return JsonResponse({"detail": "Запись не найдена"}, status=404)
        return JsonResponse({"detail": "Запись удалена"})


class DeadlineParseController(Controller[PydanticSerializer]):
    @modify(
        status_code=HTTPStatus.OK,
        extra_responses=[
            ResponseSpec(dict[str, str], status_code=HTTPStatus.UNPROCESSABLE_ENTITY),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.SERVICE_UNAVAILABLE),
        ],
    )
    def post(self, parsed_body: Body[DeadlineParseRequest]) -> DeadlinePreview:
        try:
            homework = parse_homework(parsed_body.text, parsed_body.group)
        except DeadlineClarificationRequired as exc:
            raise APIError(
                {"detail": str(exc)}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY
            ) from exc
        except DeadlineAIError as exc:
            raise APIError(
                {"detail": "Не удалось обработать дедлайн. Попробуй позже."},
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            ) from exc
        return DeadlinePreview(
            group=parsed_body.group,
            date=datetime.strptime(homework.date, "%d-%m-%Y").date(),
            subject=homework.subject.strip(),
            deadline=homework.homework.strip(),
        )


class DeadlineConfirmController(Controller[PydanticSerializer]):
    parsers = (JsonParser(), MultiPartParser())

    @modify(
        status_code=HTTPStatus.OK,
        extra_responses=[
            ResponseSpec(dict[str, str], status_code=HTTPStatus.CONFLICT),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.UNPROCESSABLE_ENTITY),
            ResponseSpec(dict[str, str], status_code=HTTPStatus.SERVICE_UNAVAILABLE),
        ],
    )
    def post(
        self,
        parsed_body: Body[DeadlineConfirmBody],
    ) -> DeadlineConfirmResponse:
        uploads = attachment_uploads(self.request)
        try:
            with attachment_transaction(uploads) as save_attachments:
                status, deadline = confirm_deadline(
                    parsed_body.group,
                    parsed_body.date,
                    parsed_body.subject,
                    parsed_body.deadline,
                )
                if uploads and status != "created":
                    raise APIError(
                        {"detail": "Дедлайн уже существует. Вложения принимаются при создании."},
                        status_code=HTTPStatus.CONFLICT,
                    )
                save_attachments(deadline)
                return DeadlineConfirmResponse(
                    status=status,
                    deadline=deadline_item(self.request, deadline, parsed_body.group),
                )
        except DeadlineAIError as exc:
            raise APIError(
                {"detail": "Не удалось проверить совпадения. Попробуй позже."},
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            ) from exc
