import pytest

from app.services.work import (
    calculate_xp,
    format_remaining,
)


@pytest.mark.parametrize(
    ("job_xp", "player_level", "required_level", "expected"),
    [
        (10, 1, 1, 10),
        (10, 2, 1, 9),
        (10, 5, 1, 6),
        (10, 20, 1, 3),
        (10, 100, 1, 3),
    ],
)
def test_calculate_xp(
    job_xp,
    player_level,
    required_level,
    expected,
):
    assert calculate_xp(
        job_xp=job_xp,
        player_level=player_level,
        required_level=required_level,
    ) == expected


def test_calculate_xp_never_returns_zero():
    assert calculate_xp(
        job_xp=1,
        player_level=100,
        required_level=1,
    ) == 1


def test_format_remaining_seconds():
    assert format_remaining(20) == "20 ثانیه"


def test_format_remaining_minutes():
    assert format_remaining(125) == "2 دقیقه و 5 ثانیه"