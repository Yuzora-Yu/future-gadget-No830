from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .config import PROTOCOL_VERSION


@dataclass(frozen=True)
class Loto7Result:
    draw: int
    draw_date: date
    main: tuple[int, ...]
    bonus: tuple[int, ...]
    source_url: str
    source_sha256: str = ""

    def validate(self) -> None:
        if not (1 <= self.draw <= 4095):
            raise ValueError("draw must be between 1 and 4095")
        if len(self.main) != 7 or len(set(self.main)) != 7:
            raise ValueError("main numbers must contain seven unique values")
        if len(self.bonus) != 2 or len(set(self.bonus)) != 2:
            raise ValueError("bonus numbers must contain two unique values")
        if any(not 1 <= number <= 37 for number in (*self.main, *self.bonus)):
            raise ValueError("all numbers must be between 1 and 37")
        if set(self.main) & set(self.bonus):
            raise ValueError("bonus numbers must not duplicate main numbers")
        if tuple(sorted(self.main)) != self.main:
            raise ValueError("main numbers must be sorted")
        if tuple(sorted(self.bonus)) != self.bonus:
            raise ValueError("bonus numbers must be sorted")

    def canonical_payload(self) -> str:
        self.validate()
        main = ",".join(f"{n:02d}" for n in self.main)
        bonus = ",".join(f"{n:02d}" for n in self.bonus)
        return (
            f"{PROTOCOL_VERSION}|draw={self.draw}|date={self.draw_date.isoformat()}|"
            f"main={main}|bonus={bonus}"
        )
