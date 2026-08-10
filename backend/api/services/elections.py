"""Election lifecycle: which election is "active", and whether one is ready
to publish. Single source of truth for "which election is live" — callers
(views, CSV auto-enrollment) must always go through get_active_election()
rather than computing it themselves."""

from django.db import IntegrityError, transaction

from api.models import Election, Position
from api.services.exceptions import (
    DuplicatePositionTitleError,
    ElectionHasBallotsError,
    ElectionLockedError,
    PublishNotReadyError,
)


def get_active_election():
    return (
        Election.objects.filter(status=Election.Status.PUBLISHED)
        .order_by("-published_at", "-created_at")
        .first()
    )


def check_publish_readiness(election):
    """Returns a list of reasons blocking publish; empty means ready.
    Publishing an empty ballot is always a mistake."""
    reasons = []
    positions = list(election.positions.all())
    if not positions:
        reasons.append("Election has no positions.")
        return reasons
    for position in positions:
        if not position.candidates.exists():
            reasons.append(f'"{position.title}" has no candidates.')
    return reasons


def publish_election(election):
    reasons = check_publish_readiness(election)
    if reasons:
        raise PublishNotReadyError(reasons)
    election.publish()
    return election


def archive_election(election):
    election.status = Election.Status.ARCHIVED
    election.save(update_fields=["status"])
    return election


def add_position(election, title, max_votes=1, order=0):
    """Blocked while status == published — broader than "voting is open",
    see 02-DATA-MODEL.md."""
    if election.status == Election.Status.PUBLISHED:
        raise ElectionLockedError(
            "Cannot add a position while the election is published."
        )
    try:
        with transaction.atomic():
            return Position.objects.create(
                election=election, title=title, max_votes=max_votes, order=order
            )
    except IntegrityError as exc:
        raise DuplicatePositionTitleError(
            f'A position titled "{title}" already exists for this election.'
        ) from exc


def delete_election(election):
    """You don't delete an election people have voted in."""
    if election.ballots.exists():
        raise ElectionHasBallotsError(
            "Cannot delete an election that already has ballots."
        )
    election.delete()
