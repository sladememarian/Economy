
import pytest

from app.services.businesses import (
    BUSINESSES,
    get_income_per_hour,
    get_upgrade_price,
)


def test_business_has_description():
    for business in BUSINESSES.values():
        assert business.description
        assert isinstance(
            business.description,
            str,
        )


def test_business_has_multipliers():
    for business in BUSINESSES.values():
        assert business.upgrade_multiplier > 1
        assert business.income_multiplier > 0


def test_income_multiplier_is_used():
    business = BUSINESSES["fast_food"]

    assert (
        get_income_per_hour(
            business,
            1,
        )
        == 250
    )


def test_income_increases_with_level():
    business = BUSINESSES["fast_food"]

    level_1 = get_income_per_hour(
        business,
        1,
    )

    level_2 = get_income_per_hour(
        business,
        2,
    )

    assert level_2 > level_1


def test_upgrade_price_increases():
    business = BUSINESSES["fast_food"]

    level_1 = get_upgrade_price(
        business,
        1,
    )

    level_2 = get_upgrade_price(
        business,
        2,
    )

    assert level_2 > level_1


def test_upgrade_price_changes_with_multiplier():
    business = BUSINESSES["fast_food"]

    assert get_upgrade_price(
        business,
        1,
    ) == 7_500


def test_max_level_enforced():
    business = BUSINESSES["fast_food"]

    with pytest.raises(ValueError):
        get_upgrade_price(
            business,
            business.max_level,
        )


def test_required_levels_are_valid():
    for business in BUSINESSES.values():
        assert business.required_level >= 1
        assert business.max_level >= business.required_level