from __future__ import annotations

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_import_rows(rows: list[dict], mapping: dict, existing_emails: set[str]) -> dict:
    errors = []
    valid_rows = []
    invalid = 0
    duplicates = 0
    seen = set()
    for i, r in enumerate(rows, start=2):
        mapped = {f: (r.get(col) or "").strip() if col else "" for f, col in mapping.items()}
        company = mapped.get("company") or ""
        email = mapped.get("email") or ""
        row_errors = []
        if not company:
            row_errors.append({"row": i, "field": "Company", "problem": "Required field missing", "suggested": "Add a company name"})
        if email and not EMAIL_RE.match(email):
            row_errors.append({"row": i, "field": "Email", "problem": "Invalid email format", "suggested": "Use name@domain.com"})
        if email and (email.lower() in existing_emails or email.lower() in seen):
            row_errors.append({"row": i, "field": "Email", "problem": "Duplicate lead", "suggested": "Skip or use a unique email"})
            duplicates += 1
        if row_errors:
            invalid += 1
            errors.extend(row_errors)
            continue
        if email:
            seen.add(email.lower())
        valid_rows.append(r)
    return {
        "total_rows": len(rows),
        "valid_rows": len(valid_rows),
        "invalid_rows": invalid,
        "duplicate_rows": duplicates,
        "missing_required_fields": sum(1 for e in errors if "missing" in e["problem"].lower()),
        "errors": errors,
        "valid": valid_rows,
    }
