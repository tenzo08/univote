from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import ChangePasswordView, EmailTokenObtainPairView, MeView
from api.views.candidates import CandidateDetailView, CandidateListCreateView
from api.views.elections import (
    ActiveElectionView,
    AddPositionView,
    ArchiveElectionView,
    ElectionDetailView,
    ElectionListCreateView,
    PublishElectionView,
)
from api.views.roster import (
    ClearRosterView,
    ElectionVoterRosterView,
    EnrollVotersView,
    UnenrollVotersView,
    VoterCsvUploadView,
)
from api.views.voting import BallotSessionView, CastBallotView

urlpatterns = [
    path("auth/login/", EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("elections/", ElectionListCreateView.as_view(), name="election-list"),
    path("elections/active/", ActiveElectionView.as_view(), name="election-active"),
    path(
        "elections/<int:election_id>/", ElectionDetailView.as_view(), name="election-detail"
    ),
    path(
        "elections/<int:election_id>/publish/",
        PublishElectionView.as_view(),
        name="election-publish",
    ),
    path(
        "elections/<int:election_id>/archive/",
        ArchiveElectionView.as_view(),
        name="election-archive",
    ),
    path(
        "elections/<int:election_id>/positions/",
        AddPositionView.as_view(),
        name="election-add-position",
    ),
    path(
        "elections/<int:election_id>/candidates/",
        CandidateListCreateView.as_view(),
        name="candidate-list",
    ),
    path(
        "elections/<int:election_id>/candidates/<int:candidate_id>/",
        CandidateDetailView.as_view(),
        name="candidate-detail",
    ),
    path("voters/upload-csv/", VoterCsvUploadView.as_view(), name="voter-upload-csv"),
    path(
        "admin/election-voter-roster/<int:election_id>/",
        ElectionVoterRosterView.as_view(),
        name="election-voter-roster",
    ),
    path(
        "admin/election-voter-roster/<int:election_id>/enroll/",
        EnrollVotersView.as_view(),
        name="election-voter-roster-enroll",
    ),
    path(
        "admin/election-voter-roster/<int:election_id>/unenroll/",
        UnenrollVotersView.as_view(),
        name="election-voter-roster-unenroll",
    ),
    path(
        "admin/election-voter-roster/<int:election_id>/clear/",
        ClearRosterView.as_view(),
        name="election-voter-roster-clear",
    ),
    path("voters/ballot-session/", BallotSessionView.as_view(), name="ballot-session"),
    path("voters/cast-ballot/", CastBallotView.as_view(), name="cast-ballot"),
]
