from django.db.models import Exists, OuterRef, Q
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Ballot, Election, ElectionEnrollment, Voter
from api.permissions import IsAdmin
from api.services.csv_import import import_voters
from api.services.enrollment import clear, enroll, unenroll


class VoterCsvUploadView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if file_obj is None:
            return Response({"detail": "No file uploaded."}, status=400)
        result = import_voters(file_obj)
        return Response(result)


class ElectionVoterRosterView(APIView):
    """Every voter, not just enrolled ones — the point of this screen is
    picking who to enroll. enrolled/has_ballot are annotated per-request,
    scoped to the one election in the URL."""

    permission_classes = [IsAdmin]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        queryset = (
            Voter.objects.select_related("user")
            .annotate(
                enrolled=Exists(
                    ElectionEnrollment.objects.filter(
                        election=election, voter=OuterRef("pk")
                    )
                ),
                has_ballot=Exists(
                    Ballot.objects.filter(election=election, voter=OuterRef("pk"))
                ),
            )
            .order_by("student_number")
        )

        q = request.query_params.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(student_number__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
            )

        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        results = [
            {
                "id": voter.id,
                "student_number": voter.student_number,
                "first_name": voter.user.first_name,
                "last_name": voter.user.last_name,
                "year_level": voter.year_level,
                "degree_program": voter.degree_program,
                "enrolled": voter.enrolled,
                "has_ballot": voter.has_ballot,
            }
            for voter in page
        ]
        return Response({"count": paginator.count, "results": results})


class EnrollVotersView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        result = enroll(election, request.data.get("voter_ids", []))
        return Response({"added": result.added, "unknown_voter_ids": result.unknown_voter_ids})


class UnenrollVotersView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        result = unenroll(election, request.data.get("voter_ids", []))
        return Response(
            {"removed": result.removed, "blocked_has_ballot": result.blocked_has_ballot}
        )


class ClearRosterView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        deleted = clear(election)
        return Response({"removed": deleted})
