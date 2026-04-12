import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, List, Tuple

from app.core.config import settings


@dataclass
class BankCsvEntry:
    date: datetime
    description: str
    amount: Decimal
    currency: str
    entry_type: str
    category: str


def _decode_csv_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _parse_amount(raw_amount: str) -> Decimal:
    cleaned = raw_amount.strip().replace(".", "").replace(",", ".").replace("+", "")
    if not cleaned:
        return Decimal("0")
    return Decimal(cleaned)


def _normalize_description(raw_text: str) -> str:
    parts = [part.strip() for part in raw_text.split("|") if part.strip()]
    candidate = parts[-1] if parts else raw_text
    collapsed = " ".join(candidate.split())
    return collapsed


def _infer_category(entry_type: str, description: str) -> str:
    lowered = description.lower()
    if entry_type == "income":
        if "gehalt" in lowered or "lohn" in lowered:
            return "Gehalt"
        return settings.INCOME_CATEGORIES[0] if settings.INCOME_CATEGORIES else "Sonstiges"
    return settings.EXPENSE_CATEGORIES[0] if settings.EXPENSE_CATEGORIES else "Sonstiges"


def parse_easybank_csv(content: bytes) -> Tuple[List[BankCsvEntry], List[str]]:
    text = _decode_csv_bytes(content)
    reader = csv.reader(text.splitlines(), delimiter=";")

    entries: List[BankCsvEntry] = []
    errors: List[str] = []

    for idx, row in enumerate(reader, start=1):
        if len(row) < 6:
            errors.append(f"Row {idx}: expected 6 columns, got {len(row)}")
            continue

        raw_description = row[1]
        raw_date = row[2]
        raw_amount = row[4]
        raw_currency = row[5]

        try:
            entry_date = datetime.strptime(raw_date.strip(), "%d.%m.%Y").date()
            amount = _parse_amount(raw_amount)
            currency = raw_currency.strip() or settings.DEFAULT_CURRENCY
            entry_type = "income" if amount > 0 else "expense"
            description = _normalize_description(raw_description)
            category = _infer_category(entry_type, description)

            entries.append(
                BankCsvEntry(
                    date=entry_date,
                    description=description,
                    amount=abs(amount),
                    currency=currency,
                    entry_type=entry_type,
                    category=category,
                )
            )
        except Exception as exc:
            errors.append(f"Row {idx}: {exc}")

    return entries, errors
