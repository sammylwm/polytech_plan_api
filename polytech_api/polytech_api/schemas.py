from datetime import date

from parser.schemas import Lesson
from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


class ScheduleRequest(BaseModel):
    group: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}$")
    start: date = Field(default_factory=date.today)
    end: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def validate_period(self) -> "ScheduleRequest":
        if self.end < self.start:
            raise ValueError("end не может быть раньше start")
        return self


class ScheduleResponse(RootModel[list[Lesson]]):
    pass


class DeadlineRequest(BaseModel):
    date: date
    subject: str
    deadline: str
    group: str = Field(pattern=r"^[0-9]{3}-[0-9]{3}$")


class DeadlineDeleteRequest(BaseModel):
    id: int


class DeadlineResponse(DeadlineRequest):
    model_config = ConfigDict(from_attributes=True)

    id: int
