from decimal import Decimal

import pytest

from chronoarb.domain.errors import CurrencyMismatchError, ValidationError
from chronoarb.domain.money import Money


class TestMoneyCreation:
    def test_create_with_valid_amount_and_currency(self):
        m = Money(amount=Decimal("100.00"), currency="USD")
        assert m.amount == Decimal("100.00")
        assert m.currency == "USD"

    def test_create_with_integer_converts_to_decimal(self):
        m = Money(amount=100, currency="USD")
        assert m.amount == Decimal("100")

    def test_create_rejects_float_amount(self):
        with pytest.raises(ValidationError, match="amount"):
            Money(amount=100.50, currency="USD")

    def test_create_rejects_invalid_currency_length(self):
        with pytest.raises(ValidationError, match="3-character"):
            Money(amount=Decimal("100"), currency="US")

    def test_create_rejects_lowercase_currency(self):
        with pytest.raises(ValidationError, match="uppercase"):
            Money(amount=Decimal("100"), currency="usd")

    def test_create_rejects_empty_currency(self):
        with pytest.raises(ValidationError):
            Money(amount=Decimal("100"), currency="")


class TestMoneyImmutability:
    def test_money_is_frozen_dataclass(self):
        m = Money(amount=Decimal("100"), currency="USD")
        with pytest.raises(Exception):
            m.amount = Decimal("200")


class TestMoneyArithmetic:
    def test_addition_same_currency(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("50"), currency="USD")
        result = m1 + m2
        assert result.amount == Decimal("150")
        assert result.currency == "USD"

    def test_subtraction_same_currency(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("30"), currency="USD")
        result = m1 - m2
        assert result.amount == Decimal("70")
        assert result.currency == "USD"

    def test_addition_currency_mismatch(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("50"), currency="EUR")
        with pytest.raises(CurrencyMismatchError):
            m1 + m2

    def test_negation(self):
        m = Money(amount=Decimal("100"), currency="USD")
        result = -m
        assert result.amount == Decimal("-100")
        assert result.currency == "USD"

    def test_multiplication(self):
        m = Money(amount=Decimal("100"), currency="USD")
        result = m * Decimal("3")
        assert result.amount == Decimal("300")
        assert result.currency == "USD"

    def test_rmultiplication(self):
        m = Money(amount=Decimal("100"), currency="USD")
        result = Decimal("3") * m
        assert result.amount == Decimal("300")
        assert result.currency == "USD"

    def test_division(self):
        m = Money(amount=Decimal("100"), currency="USD")
        result = m / Decimal("4")
        assert result.amount == Decimal("25")
        assert result.currency == "USD"

    def test_division_by_zero(self):
        m = Money(amount=Decimal("100"), currency="USD")
        with pytest.raises(ValidationError, match="zero"):
            m / Decimal("0")


class TestMoneyComparison:
    def test_equality(self):
        m1 = Money(amount=Decimal("100.00"), currency="USD")
        m2 = Money(amount=Decimal("100"), currency="USD")
        assert m1 == m2

    def test_inequality_different_amount(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("200"), currency="USD")
        assert m1 != m2

    def test_inequality_different_currency(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("100"), currency="EUR")
        assert m1 != m2

    def test_less_than(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("200"), currency="USD")
        assert m1 < m2

    def test_comparison_currency_mismatch(self):
        m1 = Money(amount=Decimal("100"), currency="USD")
        m2 = Money(amount=Decimal("50"), currency="EUR")
        with pytest.raises(CurrencyMismatchError):
            m1 < m2

    def test_not_equal_non_money(self):
        m = Money(amount=Decimal("100"), currency="USD")
        assert m != "not money"


class TestMoneyDisplay:
    def test_to_string(self):
        m = Money(amount=Decimal("100.50"), currency="USD")
        assert m.to_string() == "100.50"

    def test_decimal_precision_preserved(self):
        m = Money(
            amount=Decimal("0.10") + Decimal("0.20"), currency="USD"
        )
        assert m.amount == Decimal("0.30")
