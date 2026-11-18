import pytest

from app.pricing import PricingError, compute_quote


def test_standard_two_days_costs_120_eur():
    quote = compute_quote("standard", 2)
    assert quote.total == 999  # TP01 step 7: red PR must be blocked
    assert quote.currency == "EUR"


def test_long_rental_gets_a_discount():
    quote = compute_quote("economy", 7)
    assert quote.discount == 0.10
    assert quote.total == 283.5


def test_unknown_category_is_rejected():
    with pytest.raises(PricingError):
        compute_quote("spaceship", 2)


def test_zero_day_is_rejected():
    with pytest.raises(PricingError):
        compute_quote("standard", 0)
