import re
from datetime import date as Date
from typing import Annotated

from parser.schemas import Lesson
from pydantic import BaseModel, BeforeValidator, Field, RootModel, model_validator


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


class ScheduleResponse(RootModel[list[Lesson]]):
    pass


class DeadlineRequest(ScheduleRequest):
    pass


class DeadlineCreateRequest(DeadlineRequest):
    date: IsoDate
    subject: str
    deadline: str


class DeadlineDeleteRequest(BaseModel):
    id: int


class DeadlineItem(BaseModel):
    id: int
    date: Date
    subject: str
    deadline: str
    group: str


class DeadlineResponse(RootModel[list[DeadlineItem]]):
    pass
