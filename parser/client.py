import re
from typing import Any

import httpx

BASE_URL = "https://rasp.dmami.ru"
BPC_RE = re.compile(r"\bbpc=([\w-]+)")


class ScheduleError(Exception):
    pass


async def get_group(group: str, session: bool = False) -> dict[str, Any]:
    group = group.strip()
    if not group:
        raise ValueError("Group must not be empty")
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={
            "Referer": f"{BASE_URL}/",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "PolytechScheduleAPI/0.1",
        },
        timeout=20,
        follow_redirects=True,
    ) as client:
        for _ in range(3):
            response = await client.get(
                "/site/group", params={"group": group, "session": int(session)}
            )
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as exc:
                match = BPC_RE.search(response.text)
                if match is None:
                    raise ScheduleError("Сайт вернул некорректный JSON") from exc
                client.cookies.set("bpc", match[1], domain="rasp.dmami.ru")
                continue
            if not isinstance(data, dict):
                raise ScheduleError("Ответ расписания должен быть объектом")
            if data.get("status") not in (None, "ok"):
                raise ScheduleError(
                    str(data.get("message") or f"Группа {group} не найдена")
                )
            if not isinstance(data.get("grid"), dict):
                raise ScheduleError("В ответе отсутствует сетка расписания")
            return data
    raise ScheduleError("Не удалось получить расписание после проверки bpc")
