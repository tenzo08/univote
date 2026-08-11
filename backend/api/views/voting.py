from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Ballot
from api.permissions import CanCastBallot, IsVoter
from api.serializers import CandidateSerializer, CastBallotSerializer, PositionSerializer
from api.services.balloting import can_voter_cast, cast_ballot
from api.services.elections import get_active_election


def _build_positions(election, request):
    positions = election.positions.prefetch_related("candidates__voter__user")
    return [
        {
            **PositionSerializer(position).data,
            "candidates": CandidateSerializer(
                position.candidates.all(), many=True, context={"request": request}
            ).data,
        }
        for position in positions
    ]


class BallotSessionView(APIView):
    """Everything the ballot screen needs, in one call — see
    03-API-SPEC.md's Voting section for the exact response shape."""

    permission_classes = [IsVoter]

    def get(self, request):
        voter = request.user.voter_profile
        election = get_active_election()
        if election is None:
            return Response(
                {
                    "election": None,
                    "is_enrolled": False,
                    "has_voted": False,
                    "can_vote": False,
                    "receipt_code": None,
                    "positions": [],
                }
            )

        ballot = Ballot.objects.filter(election=election, voter=voter).first()
        is_enrolled = election.enrollments.filter(voter=voter).exists()
        can_vote, _reason = can_voter_cast(voter, election)

        return Response(
            {
                "election": {
                    "id": election.id,
                    "title": election.title,
                    "closes_at": election.closes_at,
                    "is_open_for_voting": election.is_open_for_voting,
                },
                "is_enrolled": is_enrolled,
                "has_voted": ballot is not None,
                "can_vote": can_vote,
                "receipt_code": ballot.receipt_code if ballot else None,
                "positions": _build_positions(election, request),
            }
        )


class CastBallotView(APIView):
    """Thin wrapper over services/balloting.py's cast_ballot() — every
    validation rule and the transaction boundary live there, not here."""

    permission_classes = [CanCastBallot]

    def post(self, request):
        serializer = CastBallotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        voter = request.user.voter_profile
        election = get_active_election()
        ballot = cast_ballot(voter, election, serializer.validated_data["selections"])
        return Response(
            {"detail": "Your ballot has been recorded.", "receipt_code": ballot.receipt_code},
            status=status.HTTP_201_CREATED,
        )
