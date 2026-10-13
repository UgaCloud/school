"""Read-only credit calculations and safe credit application helpers.

``StudentCredit`` is a historical ledger: a positive row represents an
overpayment source and a negative row represents an amount applied to another
bill.  The positive row must never be treated as a mutable balance because an
old row can otherwise be reused after a partial application.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app.models.fees_payment import StudentBill, StudentCredit


ZERO = Decimal("0")


@dataclass(frozen=True)
class CreditSourceSummary:
    """The usable balance from one original overpayment bill."""

    original_bill: StudentBill
    actual_overpayment: Decimal
    applied_amount: Decimal
    available_amount: Decimal
    positive_credit_total: Decimal
    legacy_available_total: Decimal
    positive_credit_rows: int


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def get_credit_source_summaries(
    student,
    *,
    include_overpayment_bills: bool = False,
    for_update: bool = False,
) -> list[CreditSourceSummary]:
    """Return one derived credit balance per original bill.

    A source's available balance is always ``cash overpayment - amounts already
    applied from that source``.  This deliberately ignores duplicate positive
    rows and the legacy ``is_applied`` flag when determining availability.
    """
    credit_qs = StudentCredit.objects.filter(student=student).select_related("original_bill")
    if for_update:
        credit_qs = credit_qs.select_for_update()
    credit_rows = list(credit_qs)

    source_ids = {row.original_bill_id for row in credit_rows if row.amount > 0}
    if include_overpayment_bills:
        source_ids.update(
            StudentBill.objects.filter(student=student).values_list("id", flat=True)
        )
    if not source_ids:
        return []

    bills_qs = StudentBill.objects.filter(id__in=source_ids).select_related("student")
    if for_update:
        bills_qs = bills_qs.select_for_update()
    bills = {bill.id: bill for bill in bills_qs}

    by_source: dict[int, list[StudentCredit]] = {}
    for row in credit_rows:
        by_source.setdefault(row.original_bill_id, []).append(row)

    summaries = []
    for source_id, bill in bills.items():
        rows = by_source.get(source_id, [])
        actual_overpayment = max(_decimal(bill.amount_paid) - _decimal(bill.total_amount), ZERO)
        applied_amount = sum(
            (-_decimal(row.amount) for row in rows if row.amount < 0),
            ZERO,
        )
        positive_rows = [row for row in rows if row.amount > 0]
        positive_credit_total = sum((_decimal(row.amount) for row in positive_rows), ZERO)
        legacy_available_total = sum(
            (_decimal(row.amount) for row in positive_rows if not row.is_applied),
            ZERO,
        )
        summaries.append(
            CreditSourceSummary(
                original_bill=bill,
                actual_overpayment=actual_overpayment,
                applied_amount=applied_amount,
                available_amount=max(actual_overpayment - applied_amount, ZERO),
                positive_credit_total=positive_credit_total,
                legacy_available_total=legacy_available_total,
                positive_credit_rows=len(positive_rows),
            )
        )

    return sorted(summaries, key=lambda summary: (summary.original_bill.bill_date, summary.original_bill.id))


def get_available_credit_total(student) -> Decimal:
    return sum(
        (summary.available_amount for summary in get_credit_source_summaries(student)),
        ZERO,
    )


def apply_credit_to_bill(*, bill: StudentBill, requested_amount) -> Decimal:
    """Apply only the still-derived credit balance to ``bill``.

    The transaction locks the target bill, source credit rows and source bills
    before posting immutable negative application rows.  It never rewrites an
    existing positive credit or historical payment.
    """
    requested_amount = _decimal(requested_amount)
    if requested_amount <= ZERO:
        return ZERO

    with transaction.atomic():
        target_bill = (
            StudentBill.objects.select_for_update()
            .select_related("student")
            .get(pk=bill.pk)
        )
        target_balance = _decimal(target_bill.balance)
        remaining_to_apply = min(requested_amount, max(target_balance, ZERO))
        if remaining_to_apply <= ZERO:
            return ZERO

        applied_amount = ZERO
        for summary in get_credit_source_summaries(
            target_bill.student,
            for_update=True,
        ):
            if summary.original_bill.id == target_bill.id or summary.available_amount <= ZERO:
                continue

            amount_from_source = min(remaining_to_apply - applied_amount, summary.available_amount)
            if amount_from_source <= ZERO:
                break

            StudentCredit.objects.create(
                student=target_bill.student,
                amount=-amount_from_source,
                description=f"Applied to bill #{target_bill.id}",
                is_applied=True,
                applied_date=timezone.localdate(),
                original_bill=summary.original_bill,
                applied_to_bill=target_bill,
            )
            applied_amount += amount_from_source
            if applied_amount >= remaining_to_apply:
                break

        return applied_amount
