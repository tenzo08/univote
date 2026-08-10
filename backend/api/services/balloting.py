"""The most important service in the codebase: whether a voter may cast a
ballot, and casting it. cast_ballot() implements the 8-step validation order
from 03-API-SPEC.md, all inside one transaction. The Ballot unique_together
constraint is the real defence against double voting under a race — this
module's job is to translate that DB-level failure into a typed exception a
view can turn into a clean error message, not a 500."""

from django.db import IntegrityError, transaction

from api.models import Ballot, BallotSelection, Candidate, ElectionEnrollment, Position
from api.services.exceptions import (
    AlreadyVotedError,
    ElectionNotOpenError,
    InvalidPositionError,
    InvalidSelectionError,
    NotEnrolledError,
)


def _is_enrolled(election, voter):
    return ElectionEnrollment.objects.filter(election=election, voter=voter).exists()


def _has_ballot(election, voter):
    return Ballot.objects.filter(election=election, voter=voter).exists()


def can_voter_cast(voter, election):
    """Non-raising — backs the read-only ballot-session screen. Checks
    must-change-password first since that's not part of cast_ballot's own
    validation list (it's gated by the CanCastBallot permission class
    instead, in Phase 3), but ballot-session has no such gate."""
    if election is None:
        return False, "No election is currently published."
    if voter.user.must_change_password:
        return False, "You must change your password before voting."
    if not _is_enrolled(election, voter):
        return False, "You are not enrolled to vote in this election."
    if _has_ballot(election, voter):
        return False, "You have already voted in this election."
    if not election.is_open_for_voting:
        return False, "Voting is not currently open for this election."
    return True, None


def _resolve_positions(election, selections):
    """Step 4: every position_id must belong to this election."""
    position_ids = [s["position_id"] for s in selections]
    positions_by_id = {
        p.id: p for p in Position.objects.filter(election=election, id__in=position_ids)
    }
    for position_id in position_ids:
        if position_id not in positions_by_id:
            raise InvalidPositionError(
                f"Position {position_id} does not belong to this election."
            )
    return positions_by_id


def _check_no_duplicate_positions(selections):
    """Step 5."""
    position_ids = [s["position_id"] for s in selections]
    if len(position_ids) != len(set(position_ids)):
        raise InvalidPositionError("Duplicate position in submission.")


def _validate_selection(election, position, candidate_ids):
    """Steps 6-8 for a single position's selection."""
    if len(candidate_ids) > position.max_votes:
        raise InvalidSelectionError(
            f'Too many candidates selected for "{position.title}" '
            f"(max {position.max_votes})."
        )
    if len(candidate_ids) != len(set(candidate_ids)):
        raise InvalidSelectionError(
            f'Duplicate candidate selected for "{position.title}".'
        )
    if not candidate_ids:
        return
    valid_candidate_ids = set(
        Candidate.objects.filter(
            id__in=candidate_ids, position=position, election=election
        ).values_list("id", flat=True)
    )
    for candidate_id in candidate_ids:
        if candidate_id not in valid_candidate_ids:
            raise InvalidSelectionError(
                f"Candidate {candidate_id} does not belong to "
                f'"{position.title}" in this election.'
            )


def _create_ballot_with_selections(election, voter, selections, positions_by_id):
    with transaction.atomic():
        try:
            ballot = Ballot.objects.create(election=election, voter=voter)
        except IntegrityError as exc:
            raise AlreadyVotedError(
                "You have already voted in this election."
            ) from exc

        for selection in selections:
            position = positions_by_id[selection["position_id"]]
            for candidate_id in selection["candidate_ids"]:
                BallotSelection.objects.create(
                    ballot=ballot, position=position, candidate_id=candidate_id
                )
    return ballot


def cast_ballot(voter, election, selections):
    """selections: [{"position_id": int, "candidate_ids": [int, ...]}, ...].
    Raises a BallotingError subclass on the first validation failure, in the
    exact 8-step order 03-API-SPEC.md specifies."""
    if election is None or not election.is_open_for_voting:
        raise ElectionNotOpenError("Voting is not currently open for this election.")
    if not _is_enrolled(election, voter):
        raise NotEnrolledError("You are not enrolled to vote in this election.")
    if _has_ballot(election, voter):
        raise AlreadyVotedError("You have already voted in this election.")

    positions_by_id = _resolve_positions(election, selections)  # step 4
    _check_no_duplicate_positions(selections)  # step 5
    for selection in selections:
        position = positions_by_id[selection["position_id"]]
        _validate_selection(election, position, selection["candidate_ids"])  # steps 6-8

    return _create_ballot_with_selections(election, voter, selections, positions_by_id)
