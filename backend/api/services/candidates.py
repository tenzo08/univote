"""Candidate registration and removal. Student-number resolution,
auto-enrollment, and the published-election lock are decisions, so they
live here rather than in the view/serializer. The election/position match
check is plain field validation and lives in the serializer instead."""

from django.db import IntegrityError, transaction

from api.models import Candidate, Election, Voter
from api.services.enrollment import enroll
from api.services.exceptions import (
    CandidateAlreadyRegisteredError,
    CandidateHasSelectionsError,
    ElectionLockedError,
    VoterNotFoundError,
)


def register_candidate(election, position, student_number, platform="", photo=None):
    if election.status == Election.Status.PUBLISHED:
        raise ElectionLockedError(
            "Cannot register a candidate while the election is published."
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
    if candidate.election.status == Election.Status.PUBLISHED:
        raise ElectionLockedError(
            "Cannot remove a candidate while the election is published."
        )
    if candidate.selections.exists():
        raise CandidateHasSelectionsError(
            "Cannot remove a candidate who already has recorded votes."
        )
    candidate.delete()
