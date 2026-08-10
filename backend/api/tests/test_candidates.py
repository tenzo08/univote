import pytest
from rest_framework.test import APIClient

from api.models import BallotSelection, Candidate, Election


@pytest.mark.django_db
class TestListCandidates:
    def test_any_authenticated_user_can_list_grouped_by_position(
        self, make_election, make_position, make_candidate, make_voter, make_user
    ):
        election = make_election()
        position = make_position(election=election, title="President")
        make_candidate(election=election, position=position, voter=make_voter())
        voter = make_user(email="reader@test.com")

        client = APIClient()
        client.force_authenticate(user=voter)
        response = client.get(f"/api/elections/{election.id}/candidates/")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["title"] == "President"
        assert len(data[0]["candidates"]) == 1
        assert "full_name" in data[0]["candidates"][0]
        assert "student_number" in data[0]["candidates"][0]

    def test_requires_authentication(self, make_election):
        election = make_election()
        response = APIClient().get(f"/api/elections/{election.id}/candidates/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestRegisterCandidate:
    def test_admin_can_register_a_candidate(
        self, make_user, make_election, make_position, make_voter
    ):
        admin = make_user(email="admin1@test.com", role="admin")
        election = make_election()
        position = make_position(election=election, title="President")
        voter = make_voter(student_number="2021-14321")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/candidates/",
            {"student_number": "2021-14321", "position": position.id, "platform": "Vote for me"},
            format="json",
        )

        assert response.status_code == 201
        candidate = Candidate.objects.get(election=election, voter=voter)
        assert candidate.platform == "Vote for me"
        assert election.enrollments.filter(voter=voter).exists()

    def test_non_admin_forbidden(self, make_user, make_election, make_position, make_voter):
        voter_user = make_user(email="notadmin@test.com")
        election = make_election()
        position = make_position(election=election)
        make_voter(student_number="2021-00099")

        client = APIClient()
        client.force_authenticate(user=voter_user)
        response = client.post(
            f"/api/elections/{election.id}/candidates/",
            {"student_number": "2021-00099", "position": position.id},
            format="json",
        )
        assert response.status_code == 403

    def test_unknown_student_number_returns_404(self, make_user, make_election, make_position):
        admin = make_user(email="admin2@test.com", role="admin")
        election = make_election()
        position = make_position(election=election)

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/candidates/",
            {"student_number": "NOBODY", "position": position.id},
            format="json",
        )
        assert response.status_code == 404

    def test_position_from_different_election_returns_400(
        self, make_user, make_election, make_position, make_voter
    ):
        admin = make_user(email="admin3@test.com", role="admin")
        election = make_election(title="A")
        other_election = make_election(title="B")
        wrong_position = make_position(election=other_election, title="Senator")
        make_voter(student_number="2021-00111")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/candidates/",
            {"student_number": "2021-00111", "position": wrong_position.id},
            format="json",
        )
        assert response.status_code == 400

    def test_blocked_while_election_published(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        admin = make_user(email="admin4@test.com", role="admin")
        election = make_election(status=Election.Status.DRAFT)
        position = make_position(election=election, title="President")
        make_candidate(election=election, position=position, voter=make_voter())
        election.publish()
        new_voter = make_voter(student_number="2021-00222")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/candidates/",
            {"student_number": "2021-00222", "position": position.id},
            format="json",
        )
        assert response.status_code == 400

    def test_duplicate_registration_for_same_position_returns_400(
        self, make_user, make_election, make_position, make_voter
    ):
        admin = make_user(email="admin-dup@test.com", role="admin")
        election = make_election()
        position = make_position(election=election, title="President")
        make_voter(student_number="2021-00555")

        client = APIClient()
        client.force_authenticate(user=admin)
        payload = {"student_number": "2021-00555", "position": position.id}
        first = client.post(
            f"/api/elections/{election.id}/candidates/", payload, format="json"
        )
        second = client.post(
            f"/api/elections/{election.id}/candidates/", payload, format="json"
        )

        assert first.status_code == 201
        assert second.status_code == 400
        assert Candidate.objects.filter(
            election=election, voter__student_number="2021-00555", position=position
        ).count() == 1

    def test_accepts_photo_as_multipart(
        self, make_user, make_election, make_position, make_voter, tiny_png
    ):
        admin = make_user(email="admin5@test.com", role="admin")
        election = make_election()
        position = make_position(election=election)
        make_voter(student_number="2021-00333")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/candidates/",
            {
                "student_number": "2021-00333",
                "position": position.id,
                "photo": tiny_png(),
            },
            format="multipart",
        )
        assert response.status_code == 201
        candidate = Candidate.objects.get(election=election, voter__student_number="2021-00333")
        assert candidate.photo.name


@pytest.mark.django_db
class TestUpdateCandidate:
    def test_admin_can_update_platform_and_photo(
        self, make_user, make_election, make_position, make_candidate, make_voter, tiny_png
    ):
        admin = make_user(email="admin6@test.com", role="admin")
        election = make_election()
        position = make_position(election=election)
        candidate = make_candidate(election=election, position=position, voter=make_voter())

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            f"/api/elections/{election.id}/candidates/{candidate.id}/",
            {"platform": "Updated platform", "photo": tiny_png()},
            format="multipart",
        )
        assert response.status_code == 200
        candidate.refresh_from_db()
        assert candidate.platform == "Updated platform"
        assert candidate.photo.name

    def test_cannot_change_voter_or_position_via_patch(
        self,
        make_user,
        make_election,
        make_position,
        make_candidate,
        make_voter,
    ):
        admin = make_user(email="admin7@test.com", role="admin")
        election = make_election()
        position = make_position(election=election, title="President")
        other_position = make_position(election=election, title="Senator")
        candidate = make_candidate(election=election, position=position, voter=make_voter())

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            f"/api/elections/{election.id}/candidates/{candidate.id}/",
            {"position": other_position.id, "platform": "New platform"},
            format="json",
        )
        assert response.status_code == 200
        candidate.refresh_from_db()
        assert candidate.position_id == position.id
        assert candidate.platform == "New platform"


@pytest.mark.django_db
class TestDeleteCandidate:
    def test_admin_can_delete_a_candidate(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        admin = make_user(email="admin8@test.com", role="admin")
        election = make_election()
        position = make_position(election=election)
        candidate = make_candidate(election=election, position=position, voter=make_voter())

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f"/api/elections/{election.id}/candidates/{candidate.id}/")

        assert response.status_code == 204
        assert not Candidate.objects.filter(pk=candidate.pk).exists()

    def test_blocked_while_election_published(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        admin = make_user(email="admin9@test.com", role="admin")
        election = make_election(status=Election.Status.DRAFT)
        position = make_position(election=election, title="President")
        candidate = make_candidate(election=election, position=position, voter=make_voter())
        election.publish()

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f"/api/elections/{election.id}/candidates/{candidate.id}/")

        assert response.status_code == 400
        assert Candidate.objects.filter(pk=candidate.pk).exists()

    def test_blocked_when_candidate_has_selections(
        self, make_user, make_election, make_position, make_candidate, make_voter, make_ballot
    ):
        admin = make_user(email="admin10@test.com", role="admin")
        election = make_election()
        position = make_position(election=election)
        candidate = make_candidate(election=election, position=position, voter=make_voter())
        ballot_voter = make_voter(student_number="2021-00444")
        ballot = make_ballot(election, ballot_voter)
        BallotSelection.objects.create(ballot=ballot, position=position, candidate=candidate)

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f"/api/elections/{election.id}/candidates/{candidate.id}/")

        assert response.status_code == 409
        assert Candidate.objects.filter(pk=candidate.pk).exists()
