from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class PairTime(BaseModel):
    start: str
    end: str


class Lesson(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    pair: int = Field(ge=1, le=7)
    start: str
    end: str
    teacher: str = ""
    rooms: list[str] = Field(default_factory=list)
    type: str = ""
    weekday: int | None = Field(default=None, ge=1, le=7)
    date_from: Date | None = None
    date_to: Date | None = None
    date: Date | None = None
    link: str | None = None

    @computed_field
    @property
    def pair_time(self) -> PairTime:
        return PairTime(start=self.start, end=self.end)

    @model_validator(mode="after")
    def validate_dates(self) -> "Lesson":
        if self.date is None and self.weekday is None:
            raise ValueError("Lesson requires a date or weekday")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be later than date_to")
        return self


class Deadline(Lesson):
    kind: Literal["lab", "practice"]
    days_left: int = Field(ge=0)
