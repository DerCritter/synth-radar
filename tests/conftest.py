"""Pytest fixtures for SynthRadar test suite.

Provides sample listing data, mock Playwright objects, mock Supabase client,
and isolated temporary configuration files.
"""

from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def sample_listing_data() -> Dict[str, Any]:
    """Fixture providing raw listing data dictionary."""
    return {
        "title": "Roland Juno-106 Synthesizer Top Zustand",
        "description": "Klassischer Analogsynthesizer voll funktionsfähig.",
        "price": 1200.0,
        "url": "https://www.kleinanzeigen.de/s-anzeige/roland-juno-106/123456",
        "image_url": "https://img.kleinanzeigen.de/api/v1/prod-ads/images/123?rule=$_59.JPG",
        "source": "Kleinanzeigen",
    }


@pytest.fixture
def sample_opportunity_data() -> Dict[str, Any]:
    """Fixture providing analyzed opportunity dictionary matching analyze_listing schema."""
    return {
        "Modelo": "Roland Juno-106",
        "Estado": "Funcional (Average)",
        "Precio URL": 1200.0,
        "Precio Mercado": "1800 - 2400 €",
        "Ahorro %": "42%",
        "Plataforma": "Kleinanzeigen",
        "Enlace": "https://www.kleinanzeigen.de/s-anzeige/roland-juno-106/123456",
        "Imagen": "https://img.kleinanzeigen.de/api/v1/prod-ads/images/123?rule=$_59.JPG",
        "Reverb": "https://reverb.com/marketplace?query=Roland+Juno-106&condition=used",
        "Mensaje Borrador": "Guten Tag, ist der Roland Juno-106 noch verfügbar?...",
        "last_seen": 1700000000.0,
        "Fecha Agregado": "29/07/2026 21:00",
    }


@pytest.fixture
def mock_playwright_page() -> AsyncMock:
    """Fixture providing an AsyncMock for Playwright Page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html><body></body></html>")
    page.mouse = AsyncMock()
    page.mouse.move = AsyncMock()
    page.mouse.wheel = AsyncMock()
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_playwright_context(mock_playwright_page: AsyncMock) -> AsyncMock:
    """Fixture providing an AsyncMock for Playwright BrowserContext object."""
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_playwright_page)
    context.close = AsyncMock()
    return context


@pytest.fixture
def mock_playwright_browser(mock_playwright_context: AsyncMock) -> AsyncMock:
    """Fixture providing an AsyncMock for Playwright Browser object."""
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=mock_playwright_context)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Fixture providing a mock Supabase client with chainable query builder methods."""
    client = MagicMock()
    table_mock = MagicMock()
    upsert_mock = MagicMock()
    select_mock = MagicMock()
    execute_mock_upsert = MagicMock()
    execute_mock_select = MagicMock()

    execute_mock_upsert.data = [{"id": 1, "modelo": "Roland Juno-106"}]
    upsert_mock.execute.return_value = execute_mock_upsert
    table_mock.upsert.return_value = upsert_mock

    execute_mock_select.data = [
        {
            "url": "https://www.kleinanzeigen.de/s-anzeige/roland-juno-106/123456",
            "modelo": "Roland Juno-106",
            "estado": "Funcional (Average)",
            "precio": 1200.0,
            "precio_mercado": "1800 - 2400 €",
            "ahorro_porcentaje": "42%",
            "plataforma": "Kleinanzeigen",
            "imagen": "https://img.kleinanzeigen.de/api/v1/prod-ads/images/123?rule=$_59.JPG",
            "reverb": "https://reverb.com/marketplace?query=Roland+Juno-106&condition=used",
            "mensaje_borrador": "Guten Tag...",
            "last_seen": 1700000000.0,
            "fecha_agregado": "29/07/2026 21:00",
        }
    ]
    select_mock.execute.return_value = execute_mock_select
    table_mock.select.return_value = select_mock

    client.table.return_value = table_mock
    return client


@pytest.fixture
def temp_config_file(tmp_path: Any) -> str:
    """Fixture providing a temporary file path for JSON config testing."""
    return str(tmp_path / "test_config.json")
