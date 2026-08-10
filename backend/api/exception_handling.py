"""Maps service-layer exceptions to HTTP status codes in one place, so
views can just call a service and let failures propagate — parse →
permission → call service → respond, no per-view try/except. Anything not
in the map falls through to DRF's default handler (serializer
ValidationError, Http404, PermissionDenied, and genuinely unmapped
exceptions all still behave exactly as DRF normally would)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from api.services.exceptions import (
    CandidateAlreadyRegisteredError,
    CandidateHasSelectionsError,
    CsvEncodingError,
    CsvTooLargeError,
    DuplicatePositionTitleError,
    ElectionHasBallotsError,
    ElectionLockedError,
    HasBallotsError,
    PublishNotReadyError,
    VoterNotFoundError,
)

# Order matters only in that isinstance() is checked top to bottom — since
# none of these currently share a base class, order is otherwise arbitrary.
EXCEPTION_STATUS_MAP = {
    PublishNotReadyError: status.HTTP_400_BAD_REQUEST,
    ElectionLockedError: status.HTTP_400_BAD_REQUEST,
    CsvTooLargeError: status.HTTP_400_BAD_REQUEST,
    CsvEncodingError: status.HTTP_400_BAD_REQUEST,
    CandidateAlreadyRegisteredError: status.HTTP_400_BAD_REQUEST,
    DuplicatePositionTitleError: status.HTTP_400_BAD_REQUEST,
    VoterNotFoundError: status.HTTP_404_NOT_FOUND,
    HasBallotsError: status.HTTP_409_CONFLICT,
    ElectionHasBallotsError: status.HTTP_409_CONFLICT,
    CandidateHasSelectionsError: status.HTTP_409_CONFLICT,
}


def custom_exception_handler(exc, context):
    for exc_class, status_code in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, exc_class):
            return Response({"detail": str(exc)}, status=status_code)
    return drf_exception_handler(exc, context)
