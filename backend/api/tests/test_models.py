from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from api.models import BallotSelection, Election, User


@pytest.mark.django_db
class TestUserVoterUniqueness:
    def test_duplicate_email_raises_integrity_error(self, make_user):
        make_user(email="dup@test.com", username="dup1")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_user(email="dup@test.com", username="dup2")

    def test_duplicate_student_number_raises_integrity_error(self, make_voter):
        make_voter(student_number="2021-00001")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_voter(student_number="2021-00001", email="other@test.com")

    def test_create_superuser_sets_admin_role_and_flags(self):
        admin = User.objects.create_superuser(
            email="admin@test.com", username="admin", password="adminpass123"
        )
        assert admin.role == User.Role.ADMIN
        assert admin.is_staff is True
        assert admin.is_superuser is True


@pytest.mark.django_db
class TestElection:
    def test_is_open_for_voting_true_only_when_published_and_in_window(self):
        # Unsaved instances — is_open_for_voting is a pure computed property,
        # and constructing several PUBLISHED rows here would collide with
        # the only_one_published_election constraint below.
        now = timezone.now()

        published_open = Election(
            status=Election.Status.PUBLISHED,
            opens_at=now - timedelta(hours=1),
            closes_at=now + timedelta(hours=1),
        )
        assert published_open.is_open_for_voting is True

        draft = Election(
            status=Election.Status.DRAFT,
            opens_at=now - timedelta(hours=1),
            closes_at=now + timedelta(hours=1),
        )
        assert draft.is_open_for_voting is False

        published_not_yet_open = Election(
            status=Election.Status.PUBLISHED,
            opens_at=now + timedelta(hours=1),
            closes_at=now + timedelta(hours=2),
        )
        assert published_not_yet_open.is_open_for_voting is False

        published_closed = Election(
            status=Election.Status.PUBLISHED,
            opens_at=now - timedelta(hours=2),
            closes_at=now - timedelta(hours=1),
        )
        assert published_closed.is_open_for_voting is False

    def test_closes_at_before_opens_at_violates_check_constraint(self, make_election):
        now = timezone.now()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_election(
                    opens_in_hours=0,
                    closes_in_hours=-1,
                )

    def test_publish_archives_previously_published_election(self, make_election):
        election_a = make_election(title="Election A", status=Election.Status.PUBLISHED)
        election_b = make_election(title="Election B", status=Election.Status.DRAFT)

        election_b.publish()
        election_a.refresh_from_db()
        election_b.refresh_from_db()

        assert election_a.status == Election.Status.ARCHIVED
        assert election_b.status == Election.Status.PUBLISHED
        assert election_b.published_at is not None

    def test_publish_does_not_archive_itself_or_unrelated_drafts(self, make_election):
        draft = make_election(title="Untouched draft", status=Election.Status.DRAFT)
        target = make_election(title="To publish", status=Election.Status.DRAFT)

        target.publish()
        draft.refresh_from_db()

        assert draft.status == Election.Status.DRAFT
        assert target.status == Election.Status.PUBLISHED

    def test_two_simultaneously_published_elections_violates_unique_constraint(
        self, make_election
    ):
        # Simulates the race publish() alone can't prevent: two elections
        # both ending up with status=published bypasses the publish() method
        # entirely (e.g. a racing second transaction). The partial unique
        # constraint is what actually stops this at the DB layer.
        make_election(title="First", status=Election.Status.PUBLISHED)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_election(title="Second", status=Election.Status.PUBLISHED)


@pytest.mark.django_db
class TestPosition:
    def test_duplicate_title_within_election_raises_integrity_error(self, make_position, make_election):
        election = make_election()
        make_position(election=election, title="President")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_position(election=election, title="President")

    def test_same_title_across_elections_is_allowed(self, make_position):
        make_position(title="President")
        make_position(title="President")  # different election per fixture default

    def test_max_votes_zero_violates_check_constraint(self, make_position):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_position(max_votes=0)


@pytest.mark.django_db
class TestCandidate:
    def test_duplicate_election_voter_position_raises_integrity_error(
        self, make_candidate, make_election, make_position, make_voter
    ):
        election = make_election()
        position = make_position(election=election)
        voter = make_voter()
        make_candidate(election=election, position=position, voter=voter)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_candidate(election=election, position=position, voter=voter)

    def test_save_rejects_position_from_different_election(
        self, make_candidate, make_election, make_position, make_voter
    ):
        election_a = make_election(title="A")
        election_b = make_election(title="B")
        position_in_b = make_position(election=election_b)
        # save() now calls clean() itself, so the mismatch is rejected at
        # creation time — not just when something remembers to call
        # .clean() afterward.
        with pytest.raises(ValidationError):
            make_candidate(election=election_a, position=position_in_b, voter=make_voter())


@pytest.mark.django_db
class TestElectionEnrollment:
    def test_duplicate_enrollment_raises_integrity_error(self, make_enrollment, make_election, make_voter):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_enrollment(election, voter)


@pytest.mark.django_db
class TestBallot:
    def test_duplicate_election_voter_ballot_raises_integrity_error(
        self, make_ballot, make_election, make_voter
    ):
        election = make_election()
        voter = make_voter()
        make_ballot(election, voter)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_ballot(election, voter)

    def test_receipt_code_is_auto_generated_and_unique(self, make_ballot, make_election, make_voter):
        election = make_election()
        ballot_1 = make_ballot(election, make_voter(student_number="A"))
        ballot_2 = make_ballot(election, make_voter(student_number="B"))
        assert ballot_1.receipt_code
        assert ballot_2.receipt_code
        assert ballot_1.receipt_code != ballot_2.receipt_code
        assert len(ballot_1.receipt_code) == 16


@pytest.mark.django_db
class TestBallotSelection:
    def test_duplicate_selection_raises_integrity_error(
        self, make_ballot, make_election, make_voter, make_candidate, make_position
    ):
        election = make_election()
        position = make_position(election=election)
        candidate = make_candidate(election=election, position=position, voter=make_voter())
        ballot = make_ballot(election, make_voter(student_number="voter-2"))

        BallotSelection.objects.create(ballot=ballot, position=position, candidate=candidate)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                BallotSelection.objects.create(
                    ballot=ballot, position=position, candidate=candidate
                )

    def test_save_rejects_candidate_from_a_different_position(
        self, make_ballot, make_election, make_voter, make_candidate, make_position
    ):
        election = make_election()
        position_a = make_position(election=election, title="President")
        position_b = make_position(election=election, title="Senator")
        candidate_for_a = make_candidate(
            election=election, position=position_a, voter=make_voter()
        )
        ballot = make_ballot(election, make_voter(student_number="voter-3"))

        with pytest.raises(ValidationError):
            BallotSelection.objects.create(
                ballot=ballot, position=position_b, candidate=candidate_for_a
            )

    def test_save_rejects_candidate_from_a_different_election(
        self, make_ballot, make_election, make_voter, make_candidate, make_position
    ):
        election_a = make_election(title="A")
        election_b = make_election(title="B")
        position_in_b = make_position(election=election_b)
        candidate_in_b = make_candidate(
            election=election_b, position=position_in_b, voter=make_voter()
        )
        ballot_in_a = make_ballot(election_a, make_voter(student_number="voter-4"))

        with pytest.raises(ValidationError):
            BallotSelection.objects.create(
                ballot=ballot_in_a, position=position_in_b, candidate=candidate_in_b
            )
