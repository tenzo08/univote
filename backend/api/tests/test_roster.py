import io
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from api.models import ElectionEnrollment
from api.services.enrollment import clear, enroll, unenroll
from api.services.exceptions import CsvTooLargeError, HasBallotsError


@pytest.mark.django_db
class TestEnroll:
    def test_adds_new_voters(self, make_election, make_voter):
        election = make_election()
        v1 = make_voter(student_number="V1")
        v2 = make_voter(student_number="V2")

        result = enroll(election, [v1.pk, v2.pk])

        assert result.added == 2
        assert result.unknown_voter_ids == []
        assert ElectionEnrollment.objects.filter(election=election).count() == 2

    def test_reports_unknown_voter_ids(self, make_election):
        election = make_election()
        result = enroll(election, [99999])
        assert result.added == 0
        assert result.unknown_voter_ids == [99999]

    def test_is_idempotent(self, make_election, make_voter):
        election = make_election()
        voter = make_voter()
        enroll(election, [voter.pk])
        result = enroll(election, [voter.pk])
        assert result.added == 0
        assert ElectionEnrollment.objects.filter(election=election, voter=voter).count() == 1


@pytest.mark.django_db
class TestUnenroll:
    def test_removes_voters_without_ballots(self, make_election, make_voter, make_enrollment):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)

        result = unenroll(election, [voter.pk])

        assert result.removed == 1
        assert result.blocked_has_ballot == []
        assert not ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_blocks_voters_with_ballots(self, make_election, make_voter, make_enrollment, make_ballot):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)
        make_ballot(election, voter)

        result = unenroll(election, [voter.pk])

        assert result.removed == 0
        assert result.blocked_has_ballot == [voter.pk]
        assert ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_no_op_for_voter_not_enrolled(self, make_election, make_voter):
        election = make_election()
        voter = make_voter()
        result = unenroll(election, [voter.pk])
        assert result.removed == 0
        assert result.blocked_has_ballot == []


@pytest.mark.django_db
class TestClear:
    def test_raises_when_ballots_exist(self, make_election, make_voter, make_enrollment, make_ballot):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)
        make_ballot(election, voter)

        with pytest.raises(HasBallotsError):
            clear(election)

        assert ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_removes_non_candidate_enrollments_but_keeps_candidates(
        self, make_election, make_voter, make_enrollment, make_position, make_candidate
    ):
        # NOTE: candidate registration doesn't yet auto-create an
        # ElectionEnrollment (that's Phase 4's admin API, per
        # 03-API-SPEC.md's candidate-creation "Behavior" list) — so both
        # rows are created explicitly here to match current real behavior.
        election = make_election()
        plain_voter = make_voter(student_number="PLAIN")
        candidate_voter = make_voter(student_number="CAND")
        make_enrollment(election, plain_voter)
        position = make_position(election=election)
        make_candidate(election=election, position=position, voter=candidate_voter)
        make_enrollment(election, candidate_voter)

        deleted = clear(election)

        assert deleted == 1
        assert not ElectionEnrollment.objects.filter(election=election, voter=plain_voter).exists()
        assert ElectionEnrollment.objects.filter(election=election, voter=candidate_voter).exists()


CSV_HEADER = "first_name,last_name,student_number,email,year_level,degree_program\n"


@pytest.mark.django_db
class TestVoterCsvUploadView:
    def test_admin_happy_path_translates_service_result(self, make_user):
        admin = make_user(email="admin-csv@test.com", role="admin")
        csv_content = CSV_HEADER + "Ana,Santos,2021-00001,ana@test.com,1,BS Computer Science\n"
        upload = io.BytesIO(csv_content.encode("utf-8"))
        upload.name = "roster.csv"

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            "/api/voters/upload-csv/", {"file": upload}, format="multipart"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert data["skipped"] == 0
        assert data["errors"] == []

    def test_csv_too_large_returns_400(self, make_user):
        admin = make_user(email="admin-csv2@test.com", role="admin")
        upload = io.BytesIO(b"whatever")
        upload.name = "roster.csv"

        client = APIClient()
        client.force_authenticate(user=admin)
        with patch(
            "api.views.roster.import_voters", side_effect=CsvTooLargeError("too big")
        ):
            response = client.post(
                "/api/voters/upload-csv/", {"file": upload}, format="multipart"
            )

        assert response.status_code == 400

    def test_non_admin_forbidden(self, make_user):
        user = make_user(email="notadmin-csv@test.com")
        upload = io.BytesIO(CSV_HEADER.encode("utf-8"))
        upload.name = "roster.csv"

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/voters/upload-csv/", {"file": upload}, format="multipart"
        )
        assert response.status_code == 403

    def test_no_file_returns_400(self, make_user):
        admin = make_user(email="admin-csv3@test.com", role="admin")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post("/api/voters/upload-csv/", {}, format="multipart")

        assert response.status_code == 400


@pytest.mark.django_db
class TestElectionVoterRosterView:
    def test_admin_lists_voters_with_enrolled_and_has_ballot_flags(
        self, make_user, make_election, make_voter, make_enrollment, make_ballot
    ):
        admin = make_user(email="admin-roster1@test.com", role="admin")
        election = make_election()
        enrolled_voter = make_voter(student_number="2021-00001")
        make_enrollment(election, enrolled_voter)
        voted_voter = make_voter(student_number="2021-00002")
        make_enrollment(election, voted_voter)
        make_ballot(election, voted_voter)
        unenrolled_voter = make_voter(student_number="2021-00003")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(f"/api/admin/election-voter-roster/{election.id}/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        by_number = {row["student_number"]: row for row in data["results"]}
        assert by_number["2021-00001"]["enrolled"] is True
        assert by_number["2021-00001"]["has_ballot"] is False
        assert by_number["2021-00002"]["has_ballot"] is True
        assert by_number["2021-00003"]["enrolled"] is False

    def test_q_filters_by_student_number(self, make_user, make_election, make_voter):
        admin = make_user(email="admin-roster2@test.com", role="admin")
        election = make_election()
        make_voter(student_number="2021-11111")
        make_voter(student_number="2021-22222")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(
            f"/api/admin/election-voter-roster/{election.id}/", {"q": "11111"}
        )
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["student_number"] == "2021-11111"

    def test_limit_offset_pagination(self, make_user, make_election, make_voter):
        admin = make_user(email="admin-roster3@test.com", role="admin")
        election = make_election()
        for i in range(5):
            make_voter(student_number=f"2021-P{i:04d}")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(
            f"/api/admin/election-voter-roster/{election.id}/", {"limit": 2, "offset": 1}
        )
        data = response.json()
        assert data["count"] == 5
        assert len(data["results"]) == 2

    def test_non_admin_forbidden(self, make_user, make_election):
        user = make_user(email="notadmin-roster@test.com")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/admin/election-voter-roster/{election.id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestEnrollVotersView:
    def test_admin_enrolls_voters(self, make_user, make_election, make_voter):
        admin = make_user(email="admin-enroll@test.com", role="admin")
        election = make_election()
        voter = make_voter(student_number="2021-33333")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/admin/election-voter-roster/{election.id}/enroll/",
            {"voter_ids": [voter.pk, 99999]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 1
        assert data["unknown_voter_ids"] == [99999]


@pytest.mark.django_db
class TestUnenrollVotersView:
    def test_admin_unenrolls_voters_and_blocks_voted_ones(
        self, make_user, make_election, make_voter, make_enrollment, make_ballot
    ):
        admin = make_user(email="admin-unenroll@test.com", role="admin")
        election = make_election()
        removable = make_voter(student_number="2021-44444")
        make_enrollment(election, removable)
        voted = make_voter(student_number="2021-55555")
        make_enrollment(election, voted)
        make_ballot(election, voted)

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/admin/election-voter-roster/{election.id}/unenroll/",
            {"voter_ids": [removable.pk, voted.pk]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["removed"] == 1
        assert data["blocked_has_ballot"] == [voted.pk]


@pytest.mark.django_db
class TestClearRosterView:
    def test_admin_clears_non_candidate_enrollments(
        self, make_user, make_election, make_voter, make_enrollment
    ):
        admin = make_user(email="admin-clear@test.com", role="admin")
        election = make_election()
        voter = make_voter(student_number="2021-66666")
        make_enrollment(election, voter)

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f"/api/admin/election-voter-roster/{election.id}/clear/")
        assert response.status_code == 200
        assert not ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_blocked_when_ballots_exist(
        self, make_user, make_election, make_voter, make_enrollment, make_ballot
    ):
        admin = make_user(email="admin-clear2@test.com", role="admin")
        election = make_election()
        voter = make_voter(student_number="2021-77777")
        make_enrollment(election, voter)
        make_ballot(election, voter)

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f"/api/admin/election-voter-roster/{election.id}/clear/")
        assert response.status_code == 409
        assert ElectionEnrollment.objects.filter(election=election, voter=voter).exists()
