#!/bin/bash
# "Just a refactor" that renames a public keyword arg and drops a public export.
source "$(dirname "$0")/common.sh" "$1"
mkdir -p billing
cat > pyproject.toml <<'T'
[project]
name = "acme-billing"
version = "1.3.0"
T
cat > billing/__init__.py <<'P'
"""Public API for acme-billing."""

__all__ = ["compute_total", "format_money"]


def compute_total(items, tax_rate=0.2):
    subtotal = sum(i["price"] * i["qty"] for i in items)
    return round(subtotal * (1 + tax_rate), 2)


def format_money(amount, currency="EUR"):
    return f"{amount:,.2f} {currency}"
P
git add -A; c 1 "feat(billing): add compute_total and format_money"
git commit -q --allow-empty -m "docs(billing): document tax_rate default"
cat > billing/totals.py <<'P'
def _subtotal(items):
    return sum(i["price"] * i["qty"] for i in items)


def compute_total(items, rate=0.2):
    return round(_subtotal(items) * (1 + rate), 2)
P
cat > billing/formatting.py <<'P'
def format_money(amount, currency="EUR"):
    return f"{amount:,.2f} {currency}"
P
cat > billing/__init__.py <<'P'
"""Public API for acme-billing."""
from billing.totals import compute_total

__all__ = ["compute_total"]
P
git add -A
