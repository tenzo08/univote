import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from api.models import Ballot, Candidate, Election, ElectionEnrollment, User, Voter


@pytest.mark.django_db
class TestSeedDemo:
    def test_first_run_without_reset_succeeds_on_empty_db(self):
        call_command("seed_demo")
        assert Election.objects.exists()

    def test_second_run_without_reset_is_refused(self):
        call_command("seed_demo", "--reset")
        with pytest.raises(CommandError):
            call_command("seed_demo")

    def test_runs_clean_twice_in_a_row_with_reset(self):
        call_command("seed_demo", "--reset")
        call_command("seed_demo", "--reset")
        assert Election.objects.filter(status=Election.Status.PUBLISHED).count() == 1

    def test_exactly_one_published_one_archived_one_draft(self):
        call_command("seed_demo", "--reset")
        assert Election.objects.filter(status=Election.Status.PUBLISHED).count() == 1
        assert Election.objects.filter(status=Election.Status.ARCHIVED).count() == 1
        assert Election.objects.filter(status=Election.Status.DRAFT).count() == 1

    def test_demo_accounts_created_with_expected_roles(self):
        call_command("seed_demo", "--reset")
        admin = User.objects.get(email="admin@test.com")
        auditor = User.objects.get(email="auditor@test.com")
        voter = User.objects.get(email="voter@test.com")
        assert admin.role == User.Role.ADMIN
        assert admin.is_superuser is True
        assert auditor.role == User.Role.AUDITOR
        assert voter.role == User.Role.VOTER
        assert Voter.objects.filter(user=voter).exists()

    def test_sample_candidate_registered_in_live_election(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        candidate_user = User.objects.get(email="candidate@test.com")
        assert Candidate.objects.filter(
            election=live, voter__user=candidate_user
        ).exists()

    def test_bulk_voters_seeded_with_roughly_one_in_seven_unenrolled(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        bulk_voters = Voter.objects.filter(
            user__email__startswith="bulkvoter"
        )
        assert bulk_voters.count() >= 50
        enrolled_count = ElectionEnrollment.objects.filter(
            election=live, voter__in=bulk_voters
        ).count()
        unenrolled_count = bulk_voters.count() - enrolled_count
        assert unenrolled_count > 0
        # "Roughly one in seven" — allow a wide tolerance rather than pin an
        # exact ratio.
        ratio = unenrolled_count / bulk_voters.count()
        assert 0.08 <= ratio <= 0.25

    def test_ballots_staggered_with_realistic_timing_shape(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        ballots = list(Ballot.objects.filter(election=live).order_by("submitted_at"))
        assert len(ballots) >= 10
        gaps = [
            (b.submitted_at - a.submitted_at).total_seconds()
            for a, b in zip(ballots, ballots[1:])
        ]
        assert any(gap < 5 for gap in gaps)
        assert any(gap > 3600 for gap in gaps)

    def test_reset_does_not_touch_unrelated_superuser(self):
        User.objects.create_superuser(
            email="realadmin@example.org", username="realadmin", password="not-a-demo-pw"
        )
        call_command("seed_demo", "--reset")
        assert User.objects.filter(email="realadmin@example.org").exists()
