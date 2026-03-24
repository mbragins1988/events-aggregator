from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.events_paginator import EventsPaginator


class TestEventsPaginator:
    @pytest.mark.asyncio
    async def test_simple_iteration(self):
        """Тест: простое получение одного события"""
        mock_client = AsyncMock()
        mock_client.get_events_page.return_value = {
            "next": None,
            "results": [{"id": "1", "name": "Event 1"}],
        }

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        event = await paginator.__anext__()

        assert event["id"] == "1"

    @pytest.mark.asyncio
    async def test_multiple_events_one_page(self):
        """Тест: несколько событий на одной странице"""
        mock_client = AsyncMock()
        mock_client.get_events_page.return_value = {
            "next": None,
            "results": [
                {"id": "1", "name": "Event 1"},
                {"id": "2", "name": "Event 2"},
            ],
        }

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        event1 = await paginator.__anext__()
        event2 = await paginator.__anext__()

        assert event1["id"] == "1"
        assert event2["id"] == "2"

    @pytest.mark.asyncio
    async def test_async_for_two_events(self):
        """Тест: async for для двух событий"""
        mock_client = AsyncMock()
        mock_client.get_events_page.return_value = {
            "next": None,
            "results": [
                {"id": "1", "name": "Event 1"},
                {"id": "2", "name": "Event 2"},
            ],
        }

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        events = []
        async for event in paginator:
            events.append(event)
            if len(events) == 2:
                break

        assert len(events) == 2
        assert events[0]["id"] == "1"
        assert events[1]["id"] == "2"

    @pytest.mark.asyncio
    async def test_get_all_one_page(self):
        """Тест: get_all() собирает все события с одной страницы"""
        mock_client = AsyncMock()
        mock_client.get_events_page.return_value = {
            "next": None,
            "results": [
                {"id": "1", "name": "Event 1"},
                {"id": "2", "name": "Event 2"},
            ],
        }

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        events = await paginator.get_all()

        assert len(events) == 2
        assert events[0]["id"] == "1"
        assert events[1]["id"] == "2"

    @pytest.mark.asyncio
    async def test_multiple_pages(self):
        """Тест: несколько страниц с курсором"""
        mock_client = AsyncMock()

        # Первая страница с курсором
        mock_client.get_events_page.side_effect = [
            {
                "next": "http://api/events?cursor=page2_cursor",
                "results": [{"id": "1", "name": "Event 1"}],
            },
            {"next": None, "results": [{"id": "2", "name": "Event 2"}]},
        ]

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        events = []
        async for event in paginator:
            events.append(event)

        assert len(events) == 2
        assert events[0]["id"] == "1"
        assert events[1]["id"] == "2"
        assert mock_client.get_events_page.call_count == 2

    @pytest.mark.asyncio
    async def test_cursor_without_next_url(self):
        """Тест: курсор есть, но next_url отсутствует"""
        mock_client = AsyncMock()
        mock_client.get_events_page.return_value = {
            "next": None,
            "results": [{"id": "1", "name": "Event 1"}],
        }

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        # Внутри paginator должен быть установлен self._cursor = None
        await paginator._load_next_page()

        assert paginator._cursor is None

    @pytest.mark.asyncio
    async def test_cursor_extraction(self):
        """Тест: извлечение курсора из URL"""
        mock_client = AsyncMock()
        mock_client.get_events_page.return_value = {
            "next": "http://api/events?changed_at=2024-01-01&cursor=test_cursor_xyz",
            "results": [{"id": "1", "name": "Event 1"}],
        }

        paginator = EventsPaginator(mock_client, changed_at=date(2024, 1, 1))

        await paginator._load_next_page()

        assert paginator._cursor == "test_cursor_xyz"
