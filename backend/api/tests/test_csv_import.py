import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from api.models import ElectionEnrollment, Election, User, Voter
from api.services.csv_import import MAX_ROWS, import_voters
from api.services.exceptions import CsvEncodingError, CsvTooLargeError

HEADER = "first_name,last_name,student_number,email,year_level,degree_program"


def _csv_file(content, name="voters.csv"):
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


@pytest.mark.django_db
class TestImportVoters:
    def test_creates_voters_from_valid_rows(self):
        content = HEADER + "\n" + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science\n"
        result = import_voters(_csv_file(content))
        assert result == {"created": 1, "skipped": 0, "errors": []}
        voter = Voter.objects.get(student_number="2021-001")
        assert voter.user.email == "ana@test.com"
        assert voter.user.role == User.Role.VOTER
        assert voter.user.must_change_password is True
        assert voter.user.check_password("2021-001")

    def test_duplicate_student_number_is_skipped_not_error(self):
        content = HEADER + "\n" + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science\n"
        import_voters(_csv_file(content))
        result = import_voters(_csv_file(content))
        assert result == {"created": 0, "skipped": 1, "errors": []}

    def test_duplicate_email_is_an_error(self):
        content = (
            HEADER
            + "\n"
            + "Ana,Santos,2021-001,dup@test.com,1,BS Computer Science\n"
            + "Ben,Cruz,2021-002,dup@test.com,1,BS Computer Science\n"
        )
        result = import_voters(_csv_file(content))
        assert result["created"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == [
            {"row": 3, "reason": "That email is already registered to another account."}
        ]

    def test_missing_required_field_is_an_error_with_correct_row_number(self):
        content = HEADER + "\n" + "Ana,Santos,,ana@test.com,1,BS Computer Science\n"
        result = import_voters(_csv_file(content))
        assert result["created"] == 0
        assert result["errors"] == [
            {"row": 2, "reason": "Missing required value(s): student_number."}
        ]

    def test_bad_row_does_not_abort_later_rows(self):
        content = (
            HEADER
            + "\n"
            + "Ana,Santos,,ana@test.com,1,BS Computer Science\n"
            + "Ben,Cruz,2021-002,ben@test.com,1,BS Computer Science\n"
        )
        result = import_voters(_csv_file(content))
        assert result["created"] == 1
        assert len(result["errors"]) == 1
        assert Voter.objects.filter(student_number="2021-002").exists()

    def test_utf8_bom_is_tolerated(self):
        content = "﻿" + HEADER + "\n" + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science\n"
        result = import_voters(_csv_file(content))
        assert result == {"created": 1, "skipped": 0, "errors": []}

    def test_case_insensitive_headers(self):
        header = "First_Name,Last_Name,Student_Number,Email,Year_Level,Degree_Program"
        content = header + "\n" + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science\n"
        result = import_voters(_csv_file(content))
        assert result == {"created": 1, "skipped": 0, "errors": []}

    def test_extra_columns_are_ignored(self):
        content = (
            HEADER
            + ",club\n"
            + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science,Debate\n"
        )
        result = import_voters(_csv_file(content))
        assert result == {"created": 1, "skipped": 0, "errors": []}

    def test_empty_file_returns_zero_result(self):
        result = import_voters(_csv_file(""))
        assert result == {"created": 0, "skipped": 0, "errors": []}

    def test_file_over_size_cap_raises(self):
        big_file = SimpleUploadedFile("voters.csv", b"x", content_type="text/csv")
        big_file.size = 6 * 1024 * 1024
        with pytest.raises(CsvTooLargeError):
            import_voters(big_file)

    def test_row_count_over_cap_raises(self):
        rows = "\n".join(
            f"F{i},L{i},2021-{i:06d},voter{i}@test.com,1,BS Computer Science"
            for i in range(MAX_ROWS + 1)
        )
        content = HEADER + "\n" + rows + "\n"
        with pytest.raises(CsvTooLargeError):
            import_voters(_csv_file(content))

    def test_auto_enrolls_into_active_election(self, make_election):
        election = make_election(status=Election.Status.PUBLISHED, opens_in_hours=-1, closes_in_hours=1)
        content = HEADER + "\n" + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science\n"
        import_voters(_csv_file(content))
        voter = Voter.objects.get(student_number="2021-001")
        assert ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_no_enrollment_attempted_when_no_active_election(self):
        content = HEADER + "\n" + "Ana,Santos,2021-001,ana@test.com,1,BS Computer Science\n"
        result = import_voters(_csv_file(content))
        assert result["created"] == 1
        assert ElectionEnrollment.objects.count() == 0

    def test_invalid_utf8_raises_encoding_error(self):
        bad_file = SimpleUploadedFile("voters.csv", b"\xff\xfe\x00\x01", content_type="text/csv")
        with pytest.raises(CsvEncodingError):
            import_voters(bad_file)

    def test_row_level_race_becomes_an_error_entry_not_a_crash(self, monkeypatch):
        """Simulates another upload's row landing between our pre-check and
        our insert — the DB unique constraint is the real defence; this
        proves the row-level IntegrityError is reported and the import
        continues, rather than aborting the whole request."""
        existing = HEADER + "\n" + "Ana,Santos,2021-999,ana@test.com,1,BS Computer Science\n"
        import_voters(_csv_file(existing))

        monkeypatch.setattr("django.db.models.query.QuerySet.exists", lambda self: False)

        content = HEADER + "\n" + "Ben,Cruz,2021-999,ben@test.com,1,BS Computer Science\n"
        result = import_voters(_csv_file(content))

        assert result["created"] == 0
        assert result["skipped"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["row"] == 2
        assert "just been created" in result["errors"][0]["reason"]
