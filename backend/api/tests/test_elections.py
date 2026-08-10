from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Election, Position
from api.services.elections import (
    add_position,
    archive_election,
    check_publish_readiness,
    delete_election,
    get_active_election,
    publish_election,
)
from api.services.exceptions import (
    ElectionHasBallotsError,
    ElectionLockedError,
    PublishNotReadyError,
)


@pytest.mark.django_db
class TestGetActiveElection:
    def test_returns_none_when_nothing_published(self, make_election):
        make_election(status=Election.Status.DRAFT)
        assert get_active_election() is None

    def test_returns_the_published_election(self, make_election):
        make_election(status=Election.Status.DRAFT)
        published = make_election(status=Election.Status.PUBLISHED)
        assert get_active_election() == published


@pytest.mark.django_db
class TestCheckPublishReadiness:
    def test_flags_election_with_no_positions(self, make_election):
        election = make_election()
        reasons = check_publish_readiness(election)
        assert reasons == ["Election has no positions."]

    def test_flags_position_with_no_candidates(self, make_election, make_position):
        election = make_election()
        make_position(election=election, title="President")
        reasons = check_publish_readiness(election)
        assert reasons == ['"President" has no candidates.']

    def test_flags_each_position_missing_candidates(
        self, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election()
        with_candidate = make_position(election=election, title="President")
        without_candidate = make_position(election=election, title="Senator")
        make_candidate(election=election, position=with_candidate, voter=make_voter())

        reasons = check_publish_readiness(election)
        assert reasons == ['"Senator" has no candidates.']
        assert without_candidate.title in reasons[0]

    def test_empty_when_every_position_has_a_candidate(
        self, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election()
        position = make_position(election=election)
        make_candidate(election=election, position=position, voter=make_voter())
        assert check_publish_readiness(election) == []


@pytest.mark.django_db
class TestPublishElection:
    def test_raises_when_not_ready(self, make_election):
        election = make_election()
        with pytest.raises(PublishNotReadyError):
            publish_election(election)
        election.refresh_from_db()
        assert election.status == Election.Status.DRAFT

    def test_publish_not_ready_error_carries_reasons(self, make_election):
        election = make_election()
        with pytest.raises(PublishNotReadyError) as exc_info:
            publish_election(election)
        assert exc_info.value.reasons == ["Election has no positions."]

    def test_publishes_and_archives_previous_when_ready(
        self, make_election, make_position, make_candidate, make_voter
    ):
        previous = make_election(title="Old", status=Election.Status.PUBLISHED)
        election = make_election(title="New")
        position = make_position(election=election)
        make_candidate(election=election, position=position, voter=make_voter())

        publish_election(election)

        election.refresh_from_db()
        previous.refresh_from_db()
        assert election.status == Election.Status.PUBLISHED
        assert previous.status == Election.Status.ARCHIVED


@pytest.mark.django_db
class TestArchiveElection:
    def test_sets_status_to_archived(self, make_election):
        election = make_election(status=Election.Status.PUBLISHED)
        archive_election(election)
        election.refresh_from_db()
        assert election.status == Election.Status.ARCHIVED


@pytest.mark.django_db
class TestAddPositionService:
    def test_creates_a_position(self, make_election):
        election = make_election()
        position = add_position(election, title="Treasurer", max_votes=1, order=2)
        assert position.election_id == election.id
        assert Position.objects.filter(election=election, title="Treasurer").exists()

    def test_raises_when_election_published(
        self, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election(status=Election.Status.DRAFT)
        position = make_position(election=election, title="President")
        make_candidate(election=election, position=position, voter=make_voter())
        election.publish()

        with pytest.raises(ElectionLockedError):
            add_position(election, title="Senator")


@pytest.mark.django_db
class TestDeleteElectionService:
    def test_deletes_when_no_ballots(self, make_election):
        election = make_election()
        delete_election(election)
        assert not Election.objects.filter(pk=election.pk).exists()

    def test_raises_when_ballots_exist(self, make_election, make_voter, make_ballot):
        election = make_election()
        voter = make_voter()
        make_ballot(election, voter)

        with pytest.raises(ElectionHasBallotsError):
            delete_election(election)
        assert Election.objects.filter(pk=election.pk).exists()


@pytest.mark.django_db
class TestElectionListView:
    def test_any_authenticated_user_can_list(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election()
        position = make_position(election=election)
        make_candidate(election=election, position=position, voter=make_voter())
        user = make_user(email="lister@test.com")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/elections/")

        assert response.status_code == 200
        data = response.json()
        item = data["results"][0]
        assert item["candidate_count"] == 1
        assert item["enrolled_count"] == 0
        assert item["ballot_count"] == 0
        assert "is_open_for_voting" in item
        assert item["positions"][0]["title"] == position.title

    def test_requires_authentication(self):
        response = APIClient().get("/api/elections/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestElectionCreateView:
    def test_admin_creates_election_with_nested_positions(self, make_user):
        admin = make_user(email="admin-create@test.com", role="admin")
        now = timezone.now()
        payload = {
            "title": "General Election 2026",
            "description": "Annual election",
            "opens_at": (now + timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=3)).isoformat(),
            "positions": [
                {"title": "President", "max_votes": 1, "order": 0},
                {"title": "Senator", "max_votes": 3, "order": 1},
            ],
        }
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post("/api/elections/", payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert len(data["positions"]) == 2

    def test_non_admin_forbidden(self, make_user):
        user = make_user(email="notadmin-create@test.com")
        now = timezone.now()
        payload = {
            "title": "General Election 2026",
            "opens_at": (now + timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=3)).isoformat(),
        }
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/elections/", payload, format="json")
        assert response.status_code == 403

    def test_rejects_closes_at_before_opens_at(self, make_user):
        admin = make_user(email="admin-create2@test.com", role="admin")
        now = timezone.now()
        payload = {
            "title": "Bad Election",
            "opens_at": (now + timedelta(days=3)).isoformat(),
            "closes_at": (now + timedelta(days=1)).isoformat(),
        }
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post("/api/elections/", payload, format="json")
        assert response.status_code == 400

    def test_rejects_duplicate_position_titles(self, make_user):
        admin = make_user(email="admin-create3@test.com", role="admin")
        now = timezone.now()
        payload = {
            "title": "Bad Election 2",
            "opens_at": (now + timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=3)).isoformat(),
            "positions": [
                {"title": "President", "max_votes": 1, "order": 0},
                {"title": "President", "max_votes": 1, "order": 1},
            ],
        }
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post("/api/elections/", payload, format="json")
        assert response.status_code == 400
        assert Election.objects.filter(title="Bad Election 2").count() == 0


@pytest.mark.django_db
class TestActiveElectionView:
    def test_returns_null_when_nothing_published(self, make_user, make_election):
        make_election(status=Election.Status.DRAFT)
        user = make_user(email="active1@test.com")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/elections/active/")
        assert response.status_code == 200
        assert response.json() is None

    def test_returns_the_published_election(self, make_user, make_election):
        published = make_election(status=Election.Status.PUBLISHED)
        user = make_user(email="active2@test.com")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/elections/active/")
        assert response.status_code == 200
        assert response.json()["id"] == published.id


@pytest.mark.django_db
class TestElectionDetailView:
    def test_any_authenticated_user_can_get(self, make_user, make_election, make_position):
        user = make_user(email="reader-detail@test.com")
        election = make_election(title="Readable Election")
        make_position(election=election, title="President")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/elections/{election.id}/")
        assert response.status_code == 200
        assert response.json()["title"] == "Readable Election"

    def test_get_requires_authentication(self, make_election):
        election = make_election()
        response = APIClient().get(f"/api/elections/{election.id}/")
        assert response.status_code == 401

    def test_admin_can_patch_title_and_dates(self, make_user, make_election):
        admin = make_user(email="admin-patch@test.com", role="admin")
        election = make_election(title="Old Title")
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            f"/api/elections/{election.id}/", {"title": "New Title"}, format="json"
        )
        assert response.status_code == 200
        election.refresh_from_db()
        assert election.title == "New Title"

    def test_patch_ignores_positions_payload(self, make_user, make_election, make_position):
        admin = make_user(email="admin-patch2@test.com", role="admin")
        election = make_election()
        make_position(election=election, title="President")
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            f"/api/elections/{election.id}/",
            {"positions": [{"title": "Sneaky", "max_votes": 1, "order": 0}]},
            format="json",
        )
        assert response.status_code == 200
        assert not Position.objects.filter(election=election, title="Sneaky").exists()

    def test_non_admin_cannot_patch(self, make_user, make_election):
        user = make_user(email="notadmin-patch@test.com")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/elections/{election.id}/", {"title": "Hacked"}, format="json"
        )
        assert response.status_code == 403

    def test_delete_succeeds_with_no_ballots(self, make_user, make_election):
        admin = make_user(email="admin-delete@test.com", role="admin")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f"/api/elections/{election.id}/")
        assert response.status_code == 204
        assert not Election.objects.filter(pk=election.pk).exists()

    def test_delete_blocked_when_ballots_exist(
        self, make_user, make_election, make_voter, make_ballot
    ):
        admin = make_user(email="admin-delete2@test.com", role="admin")
        election = make_election()
        voter = make_voter()
        make_ballot(election, voter)
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(f"/api/elections/{election.id}/")
        assert response.status_code == 409
        assert Election.objects.filter(pk=election.pk).exists()


@pytest.mark.django_db
class TestPublishElectionView:
    def test_admin_publish_succeeds_when_ready(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        admin = make_user(email="admin-publish@test.com", role="admin")
        election = make_election()
        position = make_position(election=election)
        make_candidate(election=election, position=position, voter=make_voter())
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f"/api/elections/{election.id}/publish/")
        assert response.status_code == 200
        election.refresh_from_db()
        assert election.status == Election.Status.PUBLISHED

    def test_publish_blocked_when_not_ready(self, make_user, make_election):
        admin = make_user(email="admin-publish2@test.com", role="admin")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f"/api/elections/{election.id}/publish/")
        assert response.status_code == 400
        assert "no positions" in response.json()["detail"]

    def test_non_admin_forbidden(self, make_user, make_election):
        user = make_user(email="notadmin-publish@test.com")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f"/api/elections/{election.id}/publish/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestArchiveElectionView:
    def test_admin_archive_succeeds(self, make_user, make_election):
        admin = make_user(email="admin-archive@test.com", role="admin")
        election = make_election(status=Election.Status.PUBLISHED)
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f"/api/elections/{election.id}/archive/")
        assert response.status_code == 200
        election.refresh_from_db()
        assert election.status == Election.Status.ARCHIVED


@pytest.mark.django_db
class TestAddPositionView:
    def test_admin_can_add_a_position(self, make_user, make_election):
        admin = make_user(email="admin-addpos@test.com", role="admin")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/positions/",
            {"title": "Treasurer", "max_votes": 1, "order": 0},
            format="json",
        )
        assert response.status_code == 201
        assert Position.objects.filter(election=election, title="Treasurer").exists()

    def test_blocked_while_published(
        self, make_user, make_election, make_position, make_candidate, make_voter
    ):
        admin = make_user(email="admin-addpos2@test.com", role="admin")
        election = make_election(status=Election.Status.DRAFT)
        position = make_position(election=election, title="President")
        make_candidate(election=election, position=position, voter=make_voter())
        election.publish()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/positions/",
            {"title": "Senator", "max_votes": 1, "order": 1},
            format="json",
        )
        assert response.status_code == 400
        assert not Position.objects.filter(election=election, title="Senator").exists()

    def test_duplicate_title_returns_400(self, make_user, make_election, make_position):
        admin = make_user(email="admin-addpos3@test.com", role="admin")
        election = make_election()
        make_position(election=election, title="President")
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            f"/api/elections/{election.id}/positions/",
            {"title": "President", "max_votes": 1, "order": 1},
            format="json",
        )
        assert response.status_code == 400
        assert Position.objects.filter(election=election, title="President").count() == 1

    def test_non_admin_forbidden(self, make_user, make_election):
        user = make_user(email="notadmin-addpos@test.com")
        election = make_election()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            f"/api/elections/{election.id}/positions/",
            {"title": "Treasurer", "max_votes": 1, "order": 0},
            format="json",
        )
        assert response.status_code == 403
