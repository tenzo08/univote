import pytest

from api.models import Election
from api.services.elections import (
    archive_election,
    check_publish_readiness,
    get_active_election,
    publish_election,
)
from api.services.exceptions import PublishNotReadyError


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
