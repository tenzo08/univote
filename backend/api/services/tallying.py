"""Tallying reads BallotSelection rows and nothing else — tallies are never
cached or denormalized, per the election-integrity invariant in CLAUDE.md."""

from django.db.models import Count
from django.db.models.functions import TruncHour
from django.utils import timezone

from api.models import Ballot, BallotSelection, ElectionEnrollment, User

SMALL_GROUP_THRESHOLD = 5


def can_view_results(user, election):
    """Non-admins are gated until closes_at has passed — live results
    during an open election influence turnout (03-API-SPEC.md). Admins
    always see them."""
    if user.role == User.Role.ADMIN:
        return True
    return timezone.now() > election.closes_at


def _candidate_display_name(candidate):
    user = candidate.voter.user
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or candidate.voter.student_number


def compute_results(election):
    """Per-position tallies, candidates sorted by votes descending.
    is_tied is set when the max_votes boundary — the cutoff between the
    last winning seat and the first losing one — is a tie. Never declares a
    winner; that's a decision for the electoral board."""
    results = []
    for position in election.positions.all():
        # One aggregate query per position — not one COUNT per candidate.
        vote_counts = dict(
            BallotSelection.objects.filter(position=position)
            .values("candidate_id")
            .annotate(votes=Count("id"))
            .values_list("candidate_id", "votes")
        )
        candidates = [
            {
                "candidate_id": candidate.id,
                "name": _candidate_display_name(candidate),
                "votes": vote_counts.get(candidate.id, 0),
            }
            for candidate in position.candidates.select_related("voter__user")
        ]
        candidates.sort(key=lambda c: c["votes"], reverse=True)

        is_tied = False
        if len(candidates) > position.max_votes > 0:
            boundary_votes = candidates[position.max_votes - 1]["votes"]
            next_votes = candidates[position.max_votes]["votes"]
            is_tied = boundary_votes == next_votes

        results.append(
            {
                "position": position.title,
                "max_votes": position.max_votes,
                "candidates": candidates,
                "is_tied": is_tied,
            }
        )
    return results


def compute_turnout(election):
    """turnout_pct is 0 when nobody is enrolled — never divide by zero."""
    enrolled = ElectionEnrollment.objects.filter(election=election).count()
    voted = Ballot.objects.filter(election=election).count()
    turnout_pct = round((voted / enrolled) * 100, 1) if enrolled else 0
    return {"enrolled": enrolled, "voted": voted, "turnout_pct": turnout_pct}


def _group_turnout(election, field_name):
    enrollments = ElectionEnrollment.objects.filter(election=election).select_related(
        "voter"
    )
    voted_voter_ids = set(
        Ballot.objects.filter(election=election).values_list("voter_id", flat=True)
    )

    groups = {}
    for enrollment in enrollments:
        key = getattr(enrollment.voter, field_name)
        bucket = groups.setdefault(key, {"enrolled": 0, "voted": 0})
        bucket["enrolled"] += 1
        if enrollment.voter_id in voted_voter_ids:
            bucket["voted"] += 1

    # Small groups are suppressed into a single "Other" bucket — a per-group
    # turnout figure in a program with fewer than 5 enrolled voters,
    # combined with a known cohort, can identify individuals.
    other = {"enrolled": 0, "voted": 0}
    result = []
    for key, counts in groups.items():
        if counts["enrolled"] < SMALL_GROUP_THRESHOLD:
            other["enrolled"] += counts["enrolled"]
            other["voted"] += counts["voted"]
        else:
            result.append({"group": key, **counts})
    if other["enrolled"] > 0:
        result.append({"group": "Other", **other})
    return result


def compute_turnout_breakdown(election):
    return {
        "by_year_level": _group_turnout(election, "year_level"),
        "by_degree_program": _group_turnout(election, "degree_program"),
    }


def compute_timeline(election):
    """Hourly ballot counts, ascending. Only hours with at least one ballot
    appear — no zero-filled gaps, per 03-API-SPEC.md's example."""
    rows = (
        Ballot.objects.filter(election=election)
        .annotate(hour=TruncHour("submitted_at"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )
    return [
        {"hour": row["hour"].strftime("%Y-%m-%d %H:%M"), "count": row["count"]}
        for row in rows
    ]
