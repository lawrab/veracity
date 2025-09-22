"""Basic test to verify testing infrastructure."""
import pytest


def test_basic_arithmetic():
    """Test basic arithmetic to verify pytest works."""
    assert 2 + 2 == 4


@pytest.mark.unit
def test_string_operations():
    """Test string operations."""
    text = "Veracity"
    assert text.lower() == "veracity"
    assert len(text) == 8


@pytest.mark.asyncio
async def test_async_function():
    """Test async function support."""
    import asyncio
    await asyncio.sleep(0.1)
    assert True