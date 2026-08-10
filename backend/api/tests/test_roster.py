import pytest

from api.models import ElectionEnrollment
from api.services.enrollment import clear, enroll, unenroll
from api.services.exceptions import HasBallotsError


@pytest.mark.django_db
class TestEnroll:
    def test_adds_new_voters(self, make_election, make_voter):
        election = make_election()
        v1 = make_voter(student_number="V1")
        v2 = make_voter(student_number="V2")

        result = enroll(election, [v1.pk, v2.pk])

        assert result.added == 2
        assert result.unknown_voter_ids == []
        assert ElectionEnrollment.objects.filter(election=election).count() == 2

    def test_reports_unknown_voter_ids(self, make_election):
        election = make_election()
        result = enroll(election, [99999])
        assert result.added == 0
        assert result.unknown_voter_ids == [99999]

    def test_is_idempotent(self, make_election, make_voter):
        election = make_election()
        voter = make_voter()
        enroll(election, [voter.pk])
        result = enroll(election, [voter.pk])
        assert result.added == 0
        assert ElectionEnrollment.objects.filter(election=election, voter=voter).count() == 1


@pytest.mark.django_db
class TestUnenroll:
    def test_removes_voters_without_ballots(self, make_election, make_voter, make_enrollment):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)

        result = unenroll(election, [voter.pk])

        assert result.removed == 1
        assert result.blocked_has_ballot == []
        assert not ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_blocks_voters_with_ballots(self, make_election, make_voter, make_enrollment, make_ballot):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)
        make_ballot(election, voter)

        result = unenroll(election, [voter.pk])

        assert result.removed == 0
        assert result.blocked_has_ballot == [voter.pk]
        assert ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_no_op_for_voter_not_enrolled(self, make_election, make_voter):
        election = make_election()
        voter = make_voter()
        result = unenroll(election, [voter.pk])
        assert result.removed == 0
        assert result.blocked_has_ballot == []


@pytest.mark.django_db
class TestClear:
    def test_raises_when_ballots_exist(self, make_election, make_voter, make_enrollment, make_ballot):
        election = make_election()
        voter = make_voter()
        make_enrollment(election, voter)
        make_ballot(election, voter)

        with pytest.raises(HasBallotsError):
            clear(election)

        assert ElectionEnrollment.objects.filter(election=election, voter=voter).exists()

    def test_removes_non_candidate_enrollments_but_keeps_candidates(
        self, make_election, make_voter, make_enrollment, make_position, make_candidate
    ):
        # NOTE: candidate registration doesn't yet auto-create an
        # ElectionEnrollment (that's Phase 4's admin API, per
        # 03-API-SPEC.md's candidate-creation "Behavior" list) — so both
        # rows are created explicitly here to match current real behavior.
        election = make_election()
        plain_voter = make_voter(student_number="PLAIN")
        candidate_voter = make_voter(student_number="CAND")
        make_enrollment(election, plain_voter)
        position = make_position(election=election)
        make_candidate(election=election, position=position, voter=candidate_voter)
        make_enrollment(election, candidate_voter)

        deleted = clear(election)

        assert deleted == 1
        assert not ElectionEnrollment.objects.filter(election=election, voter=plain_voter).exists()
        assert ElectionEnrollment.objects.filter(election=election, voter=candidate_voter).exists()
