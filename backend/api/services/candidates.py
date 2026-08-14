"""Candidate registration and removal. Student-number resolution,
auto-enrollment, and the published-election lock are decisions, so they
live here rather than in the view/serializer. The election/position match
check is plain field validation and lives in the serializer instead."""

from django.db import IntegrityError, transaction

from api.models import Candidate, Voter
from api.services.elections import election_is_locked
from api.services.enrollment import enroll
from api.services.exceptions import (
    CandidateAlreadyRegisteredError,
    CandidateHasSelectionsError,
    ElectionLockedError,
    VoterNotFoundError,
)


def register_candidate(election, position, student_number, platform="", photo=None):
    if election_is_locked(election):
        raise ElectionLockedError(
            "Cannot register a candidate once the election is published or has started."
        )
    try:
        voter = Voter.objects.get(student_number=student_number)
    except Voter.DoesNotExist as exc:
        raise VoterNotFoundError(
            "No voter with that student number. Import them via CSV first."
        ) from exc

    with transaction.atomic():
        try:
            candidate = Candidate.objects.create(
                election=election,
                position=position,
                voter=voter,
                platform=platform,
                photo=photo,
            )
        except IntegrityError as exc:
            raise CandidateAlreadyRegisteredError(
                "This voter is already registered as a candidate for this position."
            ) from exc
        enroll(election, [voter.pk])
    return candidate


def delete_candidate(candidate):
    """Selections are checked first so the more specific, more informative
    reason wins when both conditions hold — mirrors delete_election's
    ballots-before-started ordering."""
    if candidate.selections.exists():
        raise CandidateHasSelectionsError(
            "Cannot remove a candidate who already has recorded votes."
        )
    if election_is_locked(candidate.election):
        raise ElectionLockedError(
            "Cannot remove a candidate once the election is published or has started."
        )
    candidate.delete()
