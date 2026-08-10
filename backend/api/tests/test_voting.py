import pytest

from api.models import Ballot, BallotSelection, Election, ElectionEnrollment
from api.services.balloting import can_voter_cast, cast_ballot
from api.services.exceptions import (
    AlreadyVotedError,
    ElectionNotOpenError,
    InvalidPositionError,
    InvalidSelectionError,
    NotEnrolledError,
)


def _open_election(make_election, **kwargs):
    return make_election(
        status=Election.Status.PUBLISHED, opens_in_hours=-1, closes_in_hours=1, **kwargs
    )


@pytest.mark.django_db
class TestCanVoterCast:
    def test_false_when_no_election(self, make_voter):
        can_vote, reason = can_voter_cast(make_voter(), None)
        assert can_vote is False
        assert "No election" in reason

    def test_false_when_must_change_password(self, make_election, make_voter):
        election = _open_election(make_election)
        voter = make_voter()
        voter.user.must_change_password = True
        voter.user.save()
        can_vote, reason = can_voter_cast(voter, election)
        assert can_vote is False
        assert "password" in reason

    def test_false_when_not_enrolled(self, make_election, make_voter):
        election = _open_election(make_election)
        can_vote, reason = can_voter_cast(make_voter(), election)
        assert can_vote is False
        assert "not enrolled" in reason

    def test_false_when_already_voted(self, make_election, make_voter, make_enrollment, make_ballot):
        election = _open_election(make_election)
        voter = make_voter()
        make_enrollment(election, voter)
        make_ballot(election, voter)
        can_vote, reason = can_voter_cast(voter, election)
        assert can_vote is False
        assert "already voted" in reason

    def test_false_when_not_open(self, make_election, make_voter, make_enrollment):
        election = make_election(status=Election.Status.DRAFT)
        voter = make_voter()
        make_enrollment(election, voter)
        can_vote, reason = can_voter_cast(voter, election)
        assert can_vote is False
        assert "not currently open" in reason

    def test_true_when_everything_checks_out(self, make_election, make_voter, make_enrollment):
        election = _open_election(make_election)
        voter = make_voter()
        make_enrollment(election, voter)
        can_vote, reason = can_voter_cast(voter, election)
        assert can_vote is True
        assert reason is None


@pytest.mark.django_db
class TestCastBallot:
    def _setup(self, make_election, make_position, make_candidate, make_voter, make_enrollment):
        election = _open_election(make_election)
        position = make_position(election=election, title="President", max_votes=1)
        candidate = make_candidate(
            election=election, position=position, voter=make_voter(student_number="cand-1")
        )
        voter = make_voter(student_number="voter-1")
        make_enrollment(election, voter)
        return election, position, candidate, voter

    def test_happy_path_creates_ballot_and_selections(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election, position, candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        ballot = cast_ballot(
            voter, election, [{"position_id": position.id, "candidate_ids": [candidate.id]}]
        )
        assert ballot.receipt_code
        assert BallotSelection.objects.filter(ballot=ballot).count() == 1

    def test_undervote_empty_candidate_ids_is_valid(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election, position, candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        ballot = cast_ballot(voter, election, [{"position_id": position.id, "candidate_ids": []}])
        assert BallotSelection.objects.filter(ballot=ballot).count() == 0

    def test_omitting_a_position_entirely_is_valid(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election, position, candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        ballot = cast_ballot(voter, election, [])
        assert BallotSelection.objects.filter(ballot=ballot).count() == 0

    def test_raises_when_election_is_none(self, make_voter):
        with pytest.raises(ElectionNotOpenError):
            cast_ballot(make_voter(), None, [])

    def test_raises_when_election_is_draft(self, make_election, make_voter):
        election = make_election(status=Election.Status.DRAFT)
        with pytest.raises(ElectionNotOpenError):
            cast_ballot(make_voter(), election, [])

    def test_raises_when_election_is_archived(self, make_election, make_voter):
        election = make_election(status=Election.Status.ARCHIVED)
        with pytest.raises(ElectionNotOpenError):
            cast_ballot(make_voter(), election, [])

    def test_raises_when_published_but_not_yet_open(self, make_election, make_voter):
        election = make_election(
            status=Election.Status.PUBLISHED, opens_in_hours=1, closes_in_hours=2
        )
        with pytest.raises(ElectionNotOpenError):
            cast_ballot(make_voter(), election, [])

    def test_raises_when_published_but_closed(self, make_election, make_voter):
        election = make_election(
            status=Election.Status.PUBLISHED, opens_in_hours=-2, closes_in_hours=-1
        )
        with pytest.raises(ElectionNotOpenError):
            cast_ballot(make_voter(), election, [])

    def test_raises_when_not_enrolled(self, make_election, make_voter):
        election = _open_election(make_election)
        with pytest.raises(NotEnrolledError):
            cast_ballot(make_voter(), election, [])

    def test_raises_when_already_voted(
        self, make_election, make_voter, make_enrollment, make_ballot
    ):
        election = _open_election(make_election)
        voter = make_voter()
        make_enrollment(election, voter)
        make_ballot(election, voter)
        with pytest.raises(AlreadyVotedError):
            cast_ballot(voter, election, [])

    def test_raises_on_duplicate_position_id(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election, position, candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        with pytest.raises(InvalidPositionError):
            cast_ballot(
                voter,
                election,
                [
                    {"position_id": position.id, "candidate_ids": []},
                    {"position_id": position.id, "candidate_ids": []},
                ],
            )

    def test_raises_when_position_not_in_election(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election, position, candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        other_election = make_election(title="Other")
        other_position = make_position(election=other_election, title="Senator")
        with pytest.raises(InvalidPositionError):
            cast_ballot(
                voter, election, [{"position_id": other_position.id, "candidate_ids": []}]
            )

    def test_raises_on_duplicate_candidate_within_position(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        # max_votes=2 so the duplicate check (step 7) is exercised in
        # isolation from the max-votes check (step 6) — submitting the same
        # candidate twice must be caught even when it wouldn't otherwise
        # exceed the limit.
        election = _open_election(make_election)
        position = make_position(election=election, title="Senator", max_votes=2)
        candidate = make_candidate(
            election=election, position=position, voter=make_voter(student_number="cand-dup")
        )
        voter = make_voter(student_number="voter-dup")
        make_enrollment(election, voter)
        with pytest.raises(InvalidSelectionError):
            cast_ballot(
                voter,
                election,
                [{"position_id": position.id, "candidate_ids": [candidate.id, candidate.id]}],
            )

    def test_raises_when_too_many_candidates_selected(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election = _open_election(make_election)
        position = make_position(election=election, title="President", max_votes=1)
        c1 = make_candidate(
            election=election, position=position, voter=make_voter(student_number="c1")
        )
        c2 = make_candidate(
            election=election, position=position, voter=make_voter(student_number="c2")
        )
        voter = make_voter(student_number="voter-x")
        make_enrollment(election, voter)
        with pytest.raises(InvalidSelectionError):
            cast_ballot(
                voter, election, [{"position_id": position.id, "candidate_ids": [c1.id, c2.id]}]
            )

    def test_raises_when_candidate_belongs_to_different_position(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election = _open_election(make_election)
        position_a = make_position(election=election, title="President")
        position_b = make_position(election=election, title="Senator")
        candidate_a = make_candidate(
            election=election, position=position_a, voter=make_voter(student_number="ca")
        )
        voter = make_voter(student_number="voter-y")
        make_enrollment(election, voter)
        with pytest.raises(InvalidSelectionError):
            cast_ballot(
                voter, election, [{"position_id": position_b.id, "candidate_ids": [candidate_a.id]}]
            )

    def test_raises_when_candidate_belongs_to_different_election(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        election = _open_election(make_election)
        position = make_position(election=election, title="President")
        other_election = make_election(title="Other")
        other_position = make_position(election=other_election, title="President")
        outside_candidate = make_candidate(
            election=other_election, position=other_position, voter=make_voter(student_number="oc")
        )
        voter = make_voter(student_number="voter-z")
        make_enrollment(election, voter)
        with pytest.raises(InvalidSelectionError):
            cast_ballot(
                voter,
                election,
                [{"position_id": position.id, "candidate_ids": [outside_candidate.id]}],
            )

    def test_position_not_in_election_takes_precedence_over_duplicate_position(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        # Both selections repeat the SAME position_id that also doesn't
        # belong to this election — per 03-API-SPEC.md's numbered order,
        # step 4 (belongs to election) must fire before step 5 (duplicate).
        election, _position, _candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        other_election = make_election(title="Other")
        other_position = make_position(election=other_election, title="Senator")
        with pytest.raises(InvalidPositionError):
            cast_ballot(
                voter,
                election,
                [
                    {"position_id": other_position.id, "candidate_ids": []},
                    {"position_id": other_position.id, "candidate_ids": []},
                ],
            )

    def test_max_votes_takes_precedence_over_duplicate_candidate(
        self, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        # Same candidate repeated 3 times against max_votes=1 — per spec
        # order, step 6 (too many candidates) must fire before step 7
        # (duplicate candidate).
        election = _open_election(make_election)
        position = make_position(election=election, title="President", max_votes=1)
        candidate = make_candidate(
            election=election, position=position, voter=make_voter(student_number="cand-mv")
        )
        voter = make_voter(student_number="voter-mv")
        make_enrollment(election, voter)
        with pytest.raises(InvalidSelectionError) as exc_info:
            cast_ballot(
                voter,
                election,
                [{"position_id": position.id, "candidate_ids": [candidate.id, candidate.id, candidate.id]}],
            )
        assert "Too many candidates" in str(exc_info.value)

    def test_integrity_error_on_race_becomes_already_voted_error(
        self, monkeypatch, make_election, make_position, make_candidate, make_voter, make_enrollment
    ):
        """Simulates another transaction's ballot landing between our
        pre-check and our insert — the DB unique_together constraint is the
        real defence; this proves the service translates that IntegrityError
        into AlreadyVotedError instead of letting it become a 500."""
        election, position, candidate, voter = self._setup(
            make_election, make_position, make_candidate, make_voter, make_enrollment
        )
        Ballot.objects.create(election=election, voter=voter)

        monkeypatch.setattr("api.services.balloting._has_ballot", lambda e, v: False)

        with pytest.raises(AlreadyVotedError):
            cast_ballot(
                voter, election, [{"position_id": position.id, "candidate_ids": [candidate.id]}]
            )
        assert Ballot.objects.filter(election=election, voter=voter).count() == 1
