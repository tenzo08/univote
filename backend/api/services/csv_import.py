"""Voter CSV import. The skipped-vs-error distinction is a rule mined from
the legacy project's real use: a duplicate student_number is normal
(re-uploading a roster happens), a duplicate email is a problem. Keep it
exactly. A bad row never aborts the import — it's reported and the loop
continues, including when the row-level write itself races against a
concurrent upload."""

import csv
import io

from django.db import IntegrityError, transaction

from api.models import User, Voter
from api.services.elections import get_active_election
from api.services.enrollment import enroll
from api.services.exceptions import CsvEncodingError, CsvTooLargeError

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
REQUIRED_COLUMNS = [
    "first_name",
    "last_name",
    "student_number",
    "email",
    "year_level",
    "degree_program",
]


def _decode_csv_text(file_obj):
    raw = file_obj.read()
    try:
        return raw.decode("utf-8-sig")  # tolerates a BOM; no-op without one
    except UnicodeDecodeError as exc:
        raise CsvEncodingError("File is not valid UTF-8.") from exc


def _parse_rows(text):
    """Returns (fieldname_map, rows); fieldname_map is None for an empty
    file (no header row at all)."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return None, []
    fieldname_map = {name: name.strip().lower() for name in reader.fieldnames}
    return fieldname_map, list(reader)


def _normalize_row(raw_row, fieldname_map):
    return {
        fieldname_map[key]: (value or "").strip()
        for key, value in raw_row.items()
        if key in fieldname_map
    }


def _import_row(row, active_election):
    """Returns ("created" | "skipped" | "error", reason_or_None)."""
    if Voter.objects.filter(student_number=row["student_number"]).exists():
        return "skipped", None
    if User.objects.filter(email__iexact=row["email"]).exists():
        return "error", "That email is already registered to another account."

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=row["email"],
                username=row["student_number"],
                password=row["student_number"],
                role=User.Role.VOTER,
                must_change_password=True,
                first_name=row["first_name"],
                last_name=row["last_name"],
            )
            voter = Voter.objects.create(
                user=user,
                student_number=row["student_number"],
                year_level=row["year_level"],
                degree_program=row["degree_program"],
            )
            if active_election is not None:
                enroll(active_election, [voter.pk])
    except IntegrityError:
        # A race — e.g. a concurrent upload, or a candidate registered via
        # a different path — created a conflicting row between our checks
        # above and this write. Report it and move on; don't abort the rest
        # of the file.
        return "error", "Could not create this voter — it may have just been created by another upload."

    return "created", None


def import_voters(file_obj):
    size = getattr(file_obj, "size", None)
    if size is not None and size > MAX_FILE_SIZE_BYTES:
        raise CsvTooLargeError("File exceeds the 5 MB upload limit.")

    text = _decode_csv_text(file_obj)
    fieldname_map, rows = _parse_rows(text)
    if fieldname_map is None:
        return {"created": 0, "skipped": 0, "errors": []}
    if len(rows) > MAX_ROWS:
        raise CsvTooLargeError(f"File exceeds the {MAX_ROWS}-row limit.")

    active_election = get_active_election()
    created = 0
    skipped = 0
    errors = []

    for index, raw_row in enumerate(rows):
        row_number = index + 2  # row 2 is the first data row
        row = _normalize_row(raw_row, fieldname_map)

        missing = [col for col in REQUIRED_COLUMNS if not row.get(col)]
        if missing:
            errors.append(
                {
                    "row": row_number,
                    "reason": f"Missing required value(s): {', '.join(missing)}.",
                }
            )
            continue

        outcome, reason = _import_row(row, active_election)
        if outcome == "created":
            created += 1
        elif outcome == "skipped":
            skipped += 1
        else:
            errors.append({"row": row_number, "reason": reason})

    return {"created": created, "skipped": skipped, "errors": errors}
