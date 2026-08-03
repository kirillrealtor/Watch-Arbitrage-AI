from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

from chronoarb.domain.errors import CurrencyMismatchError, ValidationError

_VALID_CURRENCY_LENGTH: int = 3


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    DISPLAY_PRECISION: ClassVar[int] = 2

    def __post_init__(self) -> None:
        if not isinstance(self.amount, (Decimal, int)):
            raise ValidationError(
                f"Monetary amount must be Decimal or int, got {type(self.amount).__name__}"
            )
        if len(self.currency) != _VALID_CURRENCY_LENGTH:
            raise ValidationError(
                f"Currency must be a 3-character ISO 4217 code, got '{self.currency}'"
            )
        if not self.currency.isupper():
            raise ValidationError(
                f"Currency must be uppercase ISO 4217, got '{self.currency}'"
            )
        object.__setattr__(self, "amount", Decimal(str(self.amount)))

    def __add__(self, other: Money) -> Money:
        self._check_currency_match(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency_match(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __neg__(self) -> Money:
        return Money(amount=-self.amount, currency=self.currency)

    def __mul__(self, factor: Decimal | int) -> Money:
        return Money(amount=self.amount * Decimal(str(factor)), currency=self.currency)

    def __rmul__(self, factor: Decimal | int) -> Money:
        return self.__mul__(factor)

    def __truediv__(self, divisor: Decimal | int) -> Money:
        if Decimal(str(divisor)) == Decimal("0"):
            raise ValidationError("Cannot divide money by zero")
        return Money(amount=self.amount / Decimal(str(divisor)), currency=self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: Money) -> bool:
        self._check_currency_match(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._check_currency_match(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._check_currency_match(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._check_currency_match(other)
        return self.amount >= other.amount

    def to_string(self) -> str:
        return str(round(self.amount, self.DISPLAY_PRECISION))

    def _check_currency_match(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Cannot operate on {self.currency} and {other.currency}"
            )
