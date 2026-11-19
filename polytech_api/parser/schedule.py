import re
from datetime import date, datetime, timedelta
from typing import Any, Literal

from bs4 import BeautifulSoup
from pydantic import ValidationError

from .client import ScheduleError, get_group
from .schemas import Deadline, Lesson

PAIR_TIMES = {
    1: ("09:00", "10:30"),
    2: ("10:40", "12:10"),
    3: ("12:20", "13:50"),
    4: ("14:30", "16:00"),
    5: ("16:10", "17:40"),
    6: ("17:50", "19:20"),
    7: ("19:30", "21:00"),
}
DEADLINE_KEYWORDS = {
    "lab": ("лабораторн", "лаб. раб", "лаб.раб", "л/р"),
    "practice": ("практик", "практическ", "пр. зан"),
}
PARENS_RE = re.compile(r"\(([^()]*)\)")
DATE_KEY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(str(value)[:10], date_format).date()
        except ValueError:
            continue
    raise ScheduleError(f"Некорректная дата в расписании: {value}")


def _rooms(item: dict[str, Any]) -> list[str]:
    rooms = []
    for room in item.get("auditories") or []:
        if isinstance(room, dict):
            title = BeautifulSoup(str(room.get("title") or ""), "lxml").get_text(
                " ", strip=True
            )
            if title:
                rooms.append(title)
    return rooms


def parse_grid(data: dict[str, Any]) -> list[Lesson]:
    grid = data.get("grid")
    if not isinstance(grid, dict):
        raise ScheduleError("В ответе отсутствует сетка расписания")
    lessons = []
    try:
        for day_key, pairs in grid.items():
            is_dated = DATE_KEY_RE.fullmatch(str(day_key)) is not None
            lesson_date = _parse_date(day_key) if is_dated else None
            weekday = None if is_dated else int(day_key)
            if weekday is not None and not 1 <= weekday <= 7:
                raise ValueError("Weekday must be between 1 and 7")
            if isinstance(pairs, list):
                pairs = dict(enumerate(pairs, 1))
            for pair_key, items in pairs.items():
                pair = int(pair_key)
                start, end = PAIR_TIMES[pair]
                for item in items or []:
                    subject = (item.get("sbj") or item.get("subject") or "").strip()
                    if not subject:
                        continue
                    lessons.append(
                        Lesson(
                            subject=subject,
                            pair=pair,
                            start=start,
                            end=end,
                            teacher=(item.get("teacher") or "").strip(),
                            rooms=_rooms(item),
                            type=(item.get("type") or "").strip(),
                            weekday=weekday,
                            date_from=_parse_date(item.get("df")),
                            date_to=_parse_date(item.get("dt")),
                            date=lesson_date,
                            link=item.get("e_link") or None,
                        )
                    )
    except (AttributeError, TypeError, ValueError, KeyError, ValidationError) as exc:
        raise ScheduleError(f"Некорректная структура расписания: {exc}") from exc
    return lessons


def expand(lessons: list[Lesson], start: date, end: date) -> list[Lesson]:
    if end < start:
        raise ValueError("End date must not be earlier than start date")
    result = []
    for lesson in lessons:
        if lesson.date is not None:
            if start <= lesson.date <= end:
                result.append(lesson)
            continue
        if lesson.weekday is None:
            continue
        lower = max(start, lesson.date_from or start)
        upper = min(end, lesson.date_to or end)
        day = lower + timedelta(days=(lesson.weekday - 1 - lower.weekday()) % 7)
        while day <= upper:
            result.append(lesson.model_copy(update={"date": day}))
            if (upper - day).days < 7:
                break
            day += timedelta(days=7)
    result.sort(key=lambda lesson: (lesson.date or date.min, lesson.pair))
    return result


def deadline_kind(lesson: Lesson) -> Literal["lab", "practice"] | None:
    sources = [text.lower() for text in PARENS_RE.findall(lesson.subject)]
    sources.append(lesson.type.lower())
    for kind, words in DEADLINE_KEYWORDS.items():
        if any(word in source for source in sources for word in words):
            return "lab" if kind == "lab" else "practice"
    return None


def clean_subject(subject: str) -> str:
    return re.sub(r"\s+", " ", PARENS_RE.sub("", subject)).strip() or subject


def find_deadlines(lessons: list[Lesson], start: date, end: date) -> list[Deadline]:
    deadlines = []
    for lesson in expand(lessons, start, end):
        kind = deadline_kind(lesson)
        if kind is not None and lesson.date is not None:
            deadlines.append(
                Deadline(
                    **lesson.model_dump(exclude_computed_fields=True),
                    kind=kind,
                    days_left=(lesson.date - start).days,
                )
            )
    return deadlines


async def get_schedule(group: str, session: bool = False) -> list[Lesson]:
    return parse_grid(await get_group(group, session))


async def get_schedule_period(
    group: str, start: date, end: date, session: bool = False
) -> list[Lesson]:
    if end < start:
        raise ValueError("End date must not be earlier than start date")
    return expand(await get_schedule(group, session), start, end)


async def get_deadlines(
    group: str, start: date, end: date, session: bool = False
) -> list[Deadline]:
    if end < start:
        raise ValueError("End date must not be earlier than start date")
    return find_deadlines(await get_schedule(group, session), start, end)


import asyncio


async def main():
    lessons = await get_schedule("261-329")
    for lesson in lessons:
        print(lesson.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
