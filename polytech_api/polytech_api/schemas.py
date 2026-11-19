import re
from datetime import date as Date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from parser.schemas import Lesson
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    RootModel,
    StringConstraints,
    WithJsonSchema,
    model_validator,
)


def validate_date_format(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Дата должна быть в формате YYYY-MM-DD")
    return value


IsoDate = Annotated[Date, BeforeValidator(validate_date_format)]


class ScheduleRequest(BaseModel):
    group: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}$")
    start: IsoDate = Field(default_factory=Date.today)
    end: IsoDate = Field(default_factory=Date.today)

    @model_validator(mode="after")
    def validate_period(self) -> "ScheduleRequest":
        if self.end < self.start:
            raise ValueError("end не может быть раньше start")
        return self


class DeadlineRequest(ScheduleRequest):
    pass


class DeadlineCreateRequest(DeadlineRequest):
    date: IsoDate
    subject: str
    deadline: str


class DeadlineDeleteRequest(BaseModel):
    id: int


NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def current_semester() -> str:
    day = datetime.now(ZoneInfo("Europe/Moscow")).date()
    if day.month == 1:
        return f"{day.year - 1}-2"
    return f"{day.year}-{'1' if day.month < 9 else '2'}"


class SessionTaskRequest(BaseModel):
    group: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}$")
    semester: str = Field(pattern=r"^[0-9]{4}-[12]$", default_factory=current_semester)


class SessionTaskCreateRequest(SessionTaskRequest, extra="forbid"):
    subject: NonBlankText = Field(max_length=200)
    text: NonBlankText
    due_date: IsoDate | None = None


class SessionTaskTextRequest(SessionTaskRequest, extra="forbid"):
    text: NonBlankText


class SessionTaskItem(BaseModel):
    id: int
    group: str
    semester: str
    subject: str
    text: str
    due_date: Date | None


class SessionSubjectItem(BaseModel):
    subject: str
    text: str
    tasks: list[SessionTaskItem]


class SessionTaskResponse(RootModel[list[SessionSubjectItem]]):
    pass


class DeadlineParseRequest(BaseModel):
    group: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}$")
    text: NonBlankText


class DeadlineConfirmRequest(BaseModel):
    group: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}$")
    date: IsoDate
    subject: NonBlankText
    deadline: NonBlankText


class DeadlinePreview(BaseModel):
    group: str
    date: Date
    subject: str
    deadline: str


class MultipartAttachments(BaseModel):
    attachments: list[
        Annotated[str, WithJsonSchema({"type": "string", "format": "binary"})]
    ] = Field(
        default_factory=list,
        description="До пяти вложений по 20 МиБ. Добавьте отдельный элемент для каждого файла.",
    )


class DeadlineCreateForm(DeadlineCreateRequest, MultipartAttachments):
    pass


class DeadlineConfirmForm(DeadlineConfirmRequest, MultipartAttachments):
    pass


class AttachmentItem(BaseModel):
    name: str
    size: int
    url: str


class DeadlineItem(BaseModel):
    id: int
    date: Date
    subject: str
    deadline: str
    group: str
    attachments: list[AttachmentItem]


class DeadlineResponse(RootModel[list[DeadlineItem]]):
    pass


class DeadlineConfirmResponse(BaseModel):
    status: Literal["created", "updated", "unchanged"]
    deadline: DeadlineItem


class ScheduleResponse(BaseModel):
    lessons: list[Lesson]
    deadlines: list[DeadlineItem]
