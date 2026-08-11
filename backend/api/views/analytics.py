from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Election
from api.permissions import IsAuditorOrAdmin
from api.services.integrity import (
    find_rapid_succession_pairs,
    find_velocity_bursts,
    ordered_ballot_timestamps,
)
from api.services.tallying import (
    can_view_results,
    compute_results,
    compute_timeline,
    compute_turnout,
    compute_turnout_breakdown,
)

INTEGRITY_NOTE = "These are statistical signals for human review, not evidence of fraud."


class ResultsView(APIView):
    """Gated until closes_at has passed **or** the caller is an admin — live
    results during an open election influence turnout. See
    03-API-SPEC.md's Results & analytics section."""

    permission_classes = [IsAuditorOrAdmin]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        if not can_view_results(request.user, election):
            return Response(
                {"detail": "Results are not available until the election closes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "election": {
                    "id": election.id,
                    "title": election.title,
                    "closes_at": election.closes_at,
                },
                "turnout": compute_turnout(election),
                "results": compute_results(election),
            }
        )


class TurnoutView(APIView):
    permission_classes = [IsAuditorOrAdmin]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        return Response(compute_turnout_breakdown(election))


class TimelineView(APIView):
    permission_classes = [IsAuditorOrAdmin]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        return Response(compute_timeline(election))


class IntegrityReportView(APIView):
    """Never returns receipt_code or any voter identifier — timestamps and
    counts only. The note field is mandatory and must appear in the UI
    beside the results."""

    permission_classes = [IsAuditorOrAdmin]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        timestamps = ordered_ballot_timestamps(election)
        return Response(
            {
                "total_ballots": len(timestamps),
                "rapid_succession_pairs": find_rapid_succession_pairs(election, timestamps),
                "velocity_bursts": find_velocity_bursts(election, timestamps),
                "note": INTEGRITY_NOTE,
            }
        )
