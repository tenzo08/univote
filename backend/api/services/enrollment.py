"""The voter roster. Eligibility is explicit — enroll/unenroll/clear are the
only ways a voter becomes eligible to cast a ballot in an election."""

from dataclasses import dataclass, field

from api.models import Ballot, Candidate, ElectionEnrollment, Voter
from api.services.exceptions import HasBallotsError


@dataclass
class EnrollResult:
    added: int = 0
    unknown_voter_ids: list = field(default_factory=list)


@dataclass
class UnenrollResult:
    removed: int = 0
    blocked_has_ballot: list = field(default_factory=list)


def enroll(election, voter_ids):
    """Idempotent — re-enrolling an already-enrolled voter is a no-op, not
    an error."""
    result = EnrollResult()
    existing_voter_ids = set(
        Voter.objects.filter(pk__in=voter_ids).values_list("pk", flat=True)
    )
    for voter_id in voter_ids:
        if voter_id not in existing_voter_ids:
            result.unknown_voter_ids.append(voter_id)
            continue
        _, created = ElectionEnrollment.objects.get_or_create(
            election=election, voter_id=voter_id
        )
        if created:
            result.added += 1
    return result


def unenroll(election, voter_ids):
    """Voters who already voted are refused and reported — never removed.
    Removing them would silently change the turnout denominator."""
    result = UnenrollResult()
    voted_voter_ids = set(
        Ballot.objects.filter(election=election, voter_id__in=voter_ids).values_list(
            "voter_id", flat=True
        )
    )
    for voter_id in voter_ids:
        if voter_id in voted_voter_ids:
            result.blocked_has_ballot.append(voter_id)
            continue
        deleted, _ = ElectionEnrollment.objects.filter(
            election=election, voter_id=voter_id
        ).delete()
        if deleted:
            result.removed += 1
    return result


def clear(election):
    """Removes all enrollments except registered candidates. Refuses if any
    ballot exists for this election — you don't reset a roster people have
    already voted against."""
    if Ballot.objects.filter(election=election).exists():
        raise HasBallotsError(
            "Cannot clear the roster — this election already has ballots."
        )
    candidate_voter_ids = Candidate.objects.filter(election=election).values_list(
        "voter_id", flat=True
    )
    deleted, _ = (
        ElectionEnrollment.objects.filter(election=election)
        .exclude(voter_id__in=candidate_voter_ids)
        .delete()
    )
    return deleted
