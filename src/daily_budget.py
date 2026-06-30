from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DailyBudget:
    path: str
    limit: int
    _used: int = field(default=0, init=False, repr=False)
    _loaded: bool = field(default=False, init=False, repr=False)

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        p = Path(self.path)
        if not p.exists():
            self._used = 0
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data: dict[str, object] = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Corrupted budget file %s, resetting to 0", self.path)
            self._used = 0
            return
        today = date.today().isoformat()
        if data.get("date") != today:
            logger.info(
                "Daily budget reset (date changed from %s to %s)",
                data.get("date"),
                today,
            )
            self._used = 0
            return
        used_raw = data.get("used", 0)
        self._used = int(used_raw) if isinstance(used_raw, (int, float)) else 0

    def remaining(self) -> int:
        self._load()
        return max(0, self.limit - self._used)

    def can_translate(self, char_count: int) -> bool:
        return self.remaining() >= char_count

    def consume(self, char_count: int) -> None:
        self._load()
        self._used += char_count
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"date": today, "used": self._used}, f)
        logger.debug(
            "DailyBudget consumed %d chars, total=%d/%d",
            char_count,
            self._used,
            self.limit,
        )
