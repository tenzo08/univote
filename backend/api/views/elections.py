from django.db.models import Count
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Election
from api.permissions import IsAdmin
from api.serializers import (
    AddPositionSerializer,
    ElectionSerializer,
    ElectionWriteSerializer,
    PositionSerializer,
)
from api.services.elections import (
    add_position,
    archive_election,
    delete_election,
    get_active_election,
    publish_election,
    update_election,
)


def _elections_queryset():
    """Every view that returns an ElectionSerializer must use this — the
    serializer's candidate_count/enrolled_count/ballot_count fields read
    straight off these annotations. distinct=True on each Count avoids the
    join fan-out that would otherwise happen from annotating three
    unrelated reverse relations (positions/candidates, enrollments,
    ballots) on the same queryset at once."""
    return Election.objects.annotate(
        candidate_count=Count("candidates", distinct=True),
        enrolled_count=Count("enrollments", distinct=True),
        ballot_count=Count("ballots", distinct=True),
    )


class ElectionListCreateView(generics.ListCreateAPIView):
    queryset = _elections_queryset()

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return ElectionWriteSerializer if self.request.method == "POST" else ElectionSerializer

    def create(self, request, *args, **kwargs):
        serializer = ElectionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        election = serializer.save()
        annotated = _elections_queryset().get(pk=election.pk)
        return Response(ElectionSerializer(annotated).data, status=status.HTTP_201_CREATED)


class ElectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = _elections_queryset()
    lookup_url_kwarg = "election_id"

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_serializer_class(self):
        return ElectionSerializer if self.request.method == "GET" else ElectionWriteSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ElectionWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        validated_data.pop("positions", None)
        election = update_election(instance, validated_data)
        annotated = _elections_queryset().get(pk=election.pk)
        return Response(ElectionSerializer(annotated).data)

    def destroy(self, request, *args, **kwargs):
        election = self.get_object()
        delete_election(election)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActiveElectionView(APIView):
    def get(self, request):
        election = get_active_election()
        if election is None:
            # DRF's Response(None) renders an *empty* body (JSONRenderer
            # special-cases None as "no content" and strips the
            # Content-Type header) rather than the JSON literal `null` the
            # spec calls for — JsonResponse doesn't have that behavior.
            return JsonResponse(None, safe=False)
        annotated = _elections_queryset().get(pk=election.pk)
        return Response(ElectionSerializer(annotated).data)


class PublishElectionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        publish_election(election)
        annotated = _elections_queryset().get(pk=election.pk)
        return Response(ElectionSerializer(annotated).data)


class ArchiveElectionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        archive_election(election)
        annotated = _elections_queryset().get(pk=election.pk)
        return Response(ElectionSerializer(annotated).data)


class AddPositionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        serializer = AddPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        position = add_position(
            election,
            title=serializer.validated_data["title"],
            max_votes=serializer.validated_data.get("max_votes", 1),
            order=serializer.validated_data.get("order", 0),
        )
        return Response(PositionSerializer(position).data, status=status.HTTP_201_CREATED)
