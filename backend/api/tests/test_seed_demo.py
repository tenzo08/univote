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
        admin = User.objects.get(email="isabel.fernandez@up.edu.ph")
        auditor = User.objects.get(email="gabriel.santos@up.edu.ph")
        voter = User.objects.get(email="ana.delacruz@up.edu.ph")
        assert admin.role == User.Role.ADMIN
        assert admin.is_superuser is True
        assert auditor.role == User.Role.AUDITOR
        assert voter.role == User.Role.VOTER
        assert Voter.objects.filter(user=voter).exists()

    def test_all_seeded_accounts_are_up_edu_ph(self):
        call_command("seed_demo", "--reset")
        assert User.objects.count() >= 20
        assert not User.objects.exclude(email__iendswith="@up.edu.ph").exists()

    def test_sample_candidate_registered_in_live_election(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        candidate_user = User.objects.get(email="diego.mercado@up.edu.ph")
        assert Candidate.objects.filter(
            election=live, voter__user=candidate_user
        ).exists()

    def test_one_general_electorate_voter_left_unenrolled(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        unenrolled_voter = Voter.objects.get(user__email="leandro.navarro@up.edu.ph")
        assert not ElectionEnrollment.objects.filter(
            election=live, voter=unenrolled_voter
        ).exists()
        # Everyone else in the general electorate pool is enrolled.
        enrolled_count = ElectionEnrollment.objects.filter(election=live).count()
        assert enrolled_count >= 14

    def test_already_voted_sample_account_has_cast_a_ballot(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        voter = Voter.objects.get(user__email="ana.delacruz@up.edu.ph")
        assert Ballot.objects.filter(election=live, voter=voter).exists()

    def test_not_yet_voted_sample_account_is_enrolled_but_has_no_ballot(self):
        call_command("seed_demo", "--reset")
        live = Election.objects.get(status=Election.Status.PUBLISHED)
        voter = Voter.objects.get(user__email="miguel.torres@up.edu.ph")
        assert ElectionEnrollment.objects.filter(election=live, voter=voter).exists()
        assert not Ballot.objects.filter(election=live, voter=voter).exists()

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
