from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Candidate, Election
from api.permissions import IsAdmin
from api.serializers import (
    CandidateRegisterSerializer,
    CandidateSerializer,
    CandidateUpdateSerializer,
    PositionSerializer,
)
from api.services.candidates import delete_candidate, register_candidate


class CandidateListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        positions = election.positions.prefetch_related("candidates__voter__user")
        data = [
            {
                **PositionSerializer(position).data,
                "candidates": CandidateSerializer(
                    position.candidates.all(), many=True, context={"request": request}
                ).data,
            }
            for position in positions
        ]
        return Response(data)

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        serializer = CandidateRegisterSerializer(
            data=request.data, context={"election": election}
        )
        serializer.is_valid(raise_exception=True)
        candidate = register_candidate(
            election=election,
            position=serializer.validated_data["position"],
            student_number=serializer.validated_data["student_number"],
            platform=serializer.validated_data.get("platform", ""),
            photo=serializer.validated_data.get("photo"),
        )
        return Response(
            CandidateSerializer(candidate, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateDetailView(APIView):
    permission_classes = [IsAdmin]

    def _get_candidate(self, election_id, candidate_id):
        return get_object_or_404(Candidate, pk=candidate_id, election_id=election_id)

    def patch(self, request, election_id, candidate_id):
        candidate = self._get_candidate(election_id, candidate_id)
        serializer = CandidateUpdateSerializer(candidate, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CandidateSerializer(candidate, context={"request": request}).data)

    def delete(self, request, election_id, candidate_id):
        candidate = self._get_candidate(election_id, candidate_id)
        delete_candidate(candidate)
        return Response(status=status.HTTP_204_NO_CONTENT)
