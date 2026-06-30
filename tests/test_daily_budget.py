from __future__ import annotations

from pathlib import Path

import pytest

from src.daily_budget import DailyBudget


@pytest.fixture
def budget_path(tmp_path: Path) -> str:
    return str(tmp_path / "char_usage.json")


def test_remaining_returns_full_limit_when_no_file(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    assert budget.remaining() == 15000


def test_can_translate_returns_true_when_within_limit(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    assert budget.can_translate(100) is True


def test_can_translate_returns_false_when_over_limit(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=100)
    budget.consume(100)
    assert budget.can_translate(1) is False


def test_consume_reduces_remaining(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    budget.consume(3000)
    assert budget.remaining() == 12000


def test_consume_persists_to_file(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    budget.consume(5000)
    # 別インスタンスで読み直しても値が保持される
    budget2 = DailyBudget(path=budget_path, limit=15000)
    assert budget2.remaining() == 10000


def test_daily_reset_when_date_changes(budget_path: str, tmp_path: Path) -> None:
    import json

    # 昨日の日付でファイルを作成
    with open(budget_path, "w") as f:
        json.dump({"date": "2000-01-01", "used": 9000}, f)

    budget = DailyBudget(path=budget_path, limit=15000)
    # 日付が変わっているので used がリセットされる
    assert budget.remaining() == 15000


def test_consume_multiple_times(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    budget.consume(1000)
    budget.consume(2000)
    assert budget.remaining() == 12000
