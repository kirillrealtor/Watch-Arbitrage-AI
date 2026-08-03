from __future__ import annotations


class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class CurrencyMismatchError(DomainError):
    pass
