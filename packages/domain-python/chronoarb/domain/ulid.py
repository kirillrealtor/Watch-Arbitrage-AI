from __future__ import annotations

import os
import time
from typing import ClassVar


class UlidGenerator:
    PREFIX_SEPARATOR: ClassVar[str] = "_"
    ENCODING: ClassVar[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    TIMESTAMP_BITS: ClassVar[int] = 48
    RANDOM_BITS: ClassVar[int] = 80
    MAX_PREFIX_LENGTH: ClassVar[int] = 5

    def __init__(self) -> None:
        self._last_timestamp: int = 0
        self._sequence: int = 0

    def generate(self, prefix: str) -> str:
        if not prefix or len(prefix) > self.MAX_PREFIX_LENGTH:
            raise ValueError(
                f"Prefix must be 1-{self.MAX_PREFIX_LENGTH} lowercase characters, got '{prefix}'"
            )
        if not prefix.islower():
            raise ValueError(f"Prefix must be lowercase, got '{prefix}'")

        timestamp: int = int(time.time() * 1000)

        if timestamp == self._last_timestamp:
            self._sequence += 1
        else:
            self._sequence = 0
            self._last_timestamp = timestamp

        ts_encoded: str = self._encode_base32(timestamp, 10)
        rand_encoded: str = self._encode_base32(
            int.from_bytes(os.urandom(10), "big"), 16
        )
        seq_encoded: str = self._encode_base32(self._sequence, 2)

        return f"{prefix}{self.PREFIX_SEPARATOR}{ts_encoded}{rand_encoded}{seq_encoded}"

    def _encode_base32(self, value: int, length: int) -> str:
        result: list[str] = []
        for _ in range(length):
            result.append(self.ENCODING[value & 0x1F])
            value >>= 5
        return "".join(reversed(result))


_generator = UlidGenerator()


def generate_ulid(prefix: str) -> str:
    return _generator.generate(prefix)
