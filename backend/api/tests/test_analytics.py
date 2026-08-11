import pytest
from rest_framework.test import APIClient

from api.models import Ballot, Election


def _client_as(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestResultsView:
    def test_unauthenticated_returns_401(self, make_election):
        election = make_election(status=Election.Status.PUBLISHED)
        response = APIClient().get(f"/api/elections/{election.id}/results/")
        assert response.status_code == 401

    def test_voter_forbidden(self, make_user, make_election):
        voter = make_user(role="voter")
        election = make_election(status=Election.Status.PUBLISHED)
        response = _client_as(voter).get(f"/api/elections/{election.id}/results/")
        assert response.status_code == 403

    def test_unknown_election_returns_404(self, make_user):
        admin = make_user(email="admin-404@test.com", role="admin")
        response = _client_as(admin).get("/api/elections/99999/results/")
        assert response.status_code == 404

    def test_auditor_forbidden_before_close(self, make_user, make_election):
        auditor = make_user(email="auditor-early@test.com", role="auditor")
        election = make_election(status=Election.Status.PUBLISHED, closes_in_hours=1)
        response = _client_as(auditor).get(f"/api/elections/{election.id}/results/")
        assert response.status_code == 403

    def test_admin_allowed_before_close(self, make_user, make_election):
        admin = make_user(email="admin-early@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED, closes_in_hours=1)
        response = _client_as(admin).get(f"/api/elections/{election.id}/results/")
        assert response.status_code == 200

    def test_auditor_allowed_after_close(self, make_user, make_election):
        auditor = make_user(email="auditor-late@test.com", role="auditor")
        election = make_election(
            status=Election.Status.PUBLISHED, opens_in_hours=-2, closes_in_hours=-1
        )
        response = _client_as(auditor).get(f"/api/elections/{election.id}/results/")
        assert response.status_code == 200

    def test_turnout_pct_zero_when_nobody_enrolled(self, make_user, make_election):
        admin = make_user(email="admin-zero-turnout@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED, closes_in_hours=1)
        response = _client_as(admin).get(f"/api/elections/{election.id}/results/")
        assert response.status_code == 200
        assert response.json()["turnout"] == {"enrolled": 0, "voted": 0, "turnout_pct": 0}

    def test_response_shape(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        admin = make_user(email="admin-shape@test.com", role="admin")
        election = make_election(
            status=Election.Status.PUBLISHED, closes_in_hours=1, title="Shape Election"
        )
        position = make_position(election=election, title="President", max_votes=1)
        make_candidate(
            election=election, position=position, voter=make_voter(student_number="cand-shape")
        )

        response = _client_as(admin).get(f"/api/elections/{election.id}/results/")

        assert response.status_code == 200
        data = response.json()
        assert data["election"]["id"] == election.id
        assert data["election"]["title"] == "Shape Election"
        assert "turnout" in data
        assert data["results"][0]["position"] == "President"


@pytest.mark.django_db
class TestTurnoutView:
    def test_empty_breakdown_when_nobody_enrolled(self, make_user, make_election):
        admin = make_user(email="admin-turnout1@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)
        response = _client_as(admin).get(f"/api/elections/{election.id}/turnout/")
        assert response.status_code == 200
        assert response.json() == {"by_year_level": [], "by_degree_program": []}

    def test_group_of_four_suppressed_into_other(
        self, make_user, make_election, make_voter, make_enrollment
    ):
        admin = make_user(email="admin-turnout2@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)
        voters = [
            make_voter(student_number=f"grp{i}", degree_program="BS Philosophy", year_level="1")
            for i in range(4)
        ]
        for voter in voters:
            make_enrollment(election, voter)

        response = _client_as(admin).get(f"/api/elections/{election.id}/turnout/")

        assert response.status_code == 200
        groups = {g["group"] for g in response.json()["by_degree_program"]}
        assert "BS Philosophy" not in groups
        assert "Other" in groups

    def test_voter_forbidden(self, make_user, make_election):
        voter = make_user(role="voter")
        election = make_election(status=Election.Status.PUBLISHED)
        response = _client_as(voter).get(f"/api/elections/{election.id}/turnout/")
        assert response.status_code == 403

    def test_not_gated_by_close_for_auditor(self, make_user, make_election):
        # Unlike results, turnout has no spec-mandated close gate.
        auditor = make_user(email="auditor-turnout@test.com", role="auditor")
        election = make_election(status=Election.Status.PUBLISHED, closes_in_hours=1)
        response = _client_as(auditor).get(f"/api/elections/{election.id}/turnout/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestTimelineView:
    def test_returns_hourly_counts(self, make_user, make_election, make_voter):
        admin = make_user(email="admin-timeline1@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)
        Ballot.objects.create(election=election, voter=make_voter(student_number="timeline-1"))

        response = _client_as(admin).get(f"/api/elections/{election.id}/timeline/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["count"] == 1
        assert "hour" in data[0]

    def test_empty_when_no_ballots(self, make_user, make_election):
        admin = make_user(email="admin-timeline2@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)
        response = _client_as(admin).get(f"/api/elections/{election.id}/timeline/")
        assert response.status_code == 200
        assert response.json() == []

    def test_voter_forbidden(self, make_user, make_election):
        voter = make_user(role="voter")
        election = make_election(status=Election.Status.PUBLISHED)
        response = _client_as(voter).get(f"/api/elections/{election.id}/timeline/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestIntegrityReportView:
    def test_no_identifiers_in_payload(self, make_user, make_election, make_voter):
        admin = make_user(email="admin-integrity1@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)
        voter = make_voter(student_number="SECRET-999")
        Ballot.objects.create(election=election, voter=voter)

        response = _client_as(admin).get(f"/api/elections/{election.id}/integrity-report/")

        assert response.status_code == 200
        assert "SECRET-999" not in response.content.decode()
        assert "receipt_code" not in response.json()

    def test_includes_mandatory_note_and_shape(self, make_user, make_election):
        admin = make_user(email="admin-integrity2@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)

        response = _client_as(admin).get(f"/api/elections/{election.id}/integrity-report/")

        assert response.status_code == 200
        data = response.json()
        assert data["note"]
        assert "total_ballots" in data
        assert "rapid_succession_pairs" in data
        assert "velocity_bursts" in data

    def test_voter_forbidden(self, make_user, make_election):
        voter = make_user(role="voter")
        election = make_election(status=Election.Status.PUBLISHED)
        response = _client_as(voter).get(f"/api/elections/{election.id}/integrity-report/")
        assert response.status_code == 403
