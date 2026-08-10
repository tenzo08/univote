from datetime import timedelta

import pytest
from django.utils import timezone

from api.models import (
    Ballot,
    Candidate,
    Election,
    ElectionEnrollment,
    Position,
    User,
    Voter,
)


@pytest.fixture
def make_user(db):
    def _make_user(email="voter1@test.com", username=None, role=User.Role.VOTER, **kwargs):
        return User.objects.create_user(
            email=email,
            username=username or email.split("@")[0],
            password="testpass123",
            role=role,
            **kwargs,
        )

    return _make_user


@pytest.fixture
def make_voter(make_user):
    def _make_voter(
        student_number="2021-00001",
        email=None,
        year_level="1",
        degree_program="BS Computer Science",
    ):
        email = email or f"{student_number}@test.com"
        user = make_user(email=email, username=student_number, role=User.Role.VOTER)
        return Voter.objects.create(
            user=user,
            student_number=student_number,
            year_level=year_level,
            degree_program=degree_program,
        )

    return _make_voter


@pytest.fixture
def make_election(db):
    def _make_election(
        title="Test Election",
        status=Election.Status.DRAFT,
        opens_in_hours=-1,
        closes_in_hours=1,
        **kwargs,
    ):
        now = timezone.now()
        return Election.objects.create(
            title=title,
            status=status,
            opens_at=now + timedelta(hours=opens_in_hours),
            closes_at=now + timedelta(hours=closes_in_hours),
            **kwargs,
        )

    return _make_election


@pytest.fixture
def make_position(make_election):
    def _make_position(election=None, title="President", max_votes=1, order=0):
        election = election or make_election()
        return Position.objects.create(
            election=election, title=title, max_votes=max_votes, order=order
        )

    return _make_position


@pytest.fixture
def make_candidate(make_position, make_voter):
    def _make_candidate(election=None, position=None, voter=None, **kwargs):
        position = position or make_position(election=election)
        election = election or position.election
        voter = voter or make_voter()
        return Candidate.objects.create(
            election=election, position=position, voter=voter, **kwargs
        )

    return _make_candidate


@pytest.fixture
def make_enrollment(db):
    def _make_enrollment(election, voter):
        return ElectionEnrollment.objects.create(election=election, voter=voter)

    return _make_enrollment


@pytest.fixture
def make_ballot(db):
    def _make_ballot(election, voter):
        return Ballot.objects.create(election=election, voter=voter)

    return _make_ballot
