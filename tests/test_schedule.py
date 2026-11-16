import unittest
from datetime import date
from unittest.mock import patch

import httpx

from parser import (
    ScheduleError,
    expand,
    find_deadlines,
    get_group,
    get_schedule,
    parse_grid,
)


class ScheduleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.data = {
            "grid": {
                "1": {
                    "1": [
                        {
                            "sbj": "Физика (лабораторная работа)",
                            "df": "01.09.2026",
                            "dt": "2026-11-01",
                            "auditories": [{"title": "<a>Пр2302 &amp; 2303</a>"}],
                        }
                    ],
                },
                "2": [],
                "2026-11-02": {"2": [{"subject": "Экзамен"}]},
            },
        }

    def test_dates_rooms_and_deadlines(self) -> None:
        lessons = parse_grid(self.data)
        self.assertEqual(lessons[0].rooms, ["Пр2302 & 2303"])
        expanded = expand(lessons, date(2026, 10, 25), date(2026, 11, 8))
        self.assertEqual(
            [item.date for item in expanded], [date(2026, 10, 26), date(2026, 11, 2)]
        )
        deadlines = find_deadlines(lessons, date(2026, 10, 25), date(2026, 11, 8))
        self.assertEqual(len(deadlines), 1)
        self.assertEqual(deadlines[0].kind, "lab")
        self.assertEqual(deadlines[0].days_left, 1)
        self.assertEqual(deadlines[0].model_dump(mode="json")["date"], "2026-10-26")
        self.assertIsNone(lessons[0].date)

    def test_invalid_data_and_period(self) -> None:
        for data in (
            {},
            {"grid": {"8": {}}},
            {"grid": {"1": {"9": []}}},
            {"grid": {"2026-99-01": {}}},
        ):
            with self.subTest(data=data), self.assertRaises(ScheduleError):
                parse_grid(data)
        with self.assertRaises(ValueError):
            expand([], date(2026, 11, 2), date(2026, 11, 1))

    async def test_cookie_retry_and_query_encoding(self) -> None:
        requests = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(200, text="document.cookie='bpc=token123'")
            self.assertIn("bpc=token123", request.headers["cookie"])
            return httpx.Response(200, json=self.data)

        client = httpx.AsyncClient(
            base_url="https://rasp.dmami.ru", transport=httpx.MockTransport(handle)
        )
        with patch("parser.client.httpx.AsyncClient", return_value=client):
            lessons = await get_schedule(" 231 &321 ", session=True)
        self.assertEqual(len(lessons), 2)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[-1].url.params["group"], "231 &321")
        self.assertEqual(requests[-1].url.params["session"], "1")
        self.assertTrue(client.is_closed)

    async def test_invalid_responses_and_http_errors(self) -> None:
        responses = [
            httpx.Response(200, json=[]),
            httpx.Response(200, json={"status": "error"}),
            httpx.Response(200, json={"grid": None}),
            httpx.Response(200, text="invalid"),
            httpx.Response(503),
        ]
        for response in responses:
            with self.subTest(response=response):
                transport = httpx.MockTransport(
                    lambda request, response=response: response
                )
                client = httpx.AsyncClient(
                    base_url="https://rasp.dmami.ru", transport=transport
                )
                with (
                    patch("parser.client.httpx.AsyncClient", return_value=client),
                    self.assertRaises(
                        httpx.HTTPStatusError
                        if response.status_code == 503
                        else ScheduleError
                    ),
                ):
                    await get_group("231-321")


if __name__ == "__main__":
    unittest.main()
