from datetime import timedelta

import pytest
from django.utils import timezone

from api.models import Ballot
from api.services.integrity import find_rapid_succession_pairs, find_velocity_bursts


def _ballot_at(election, voter, when):
    ballot = Ballot.objects.create(election=election, voter=voter)
    Ballot.objects.filter(pk=ballot.pk).update(submitted_at=when)
    ballot.refresh_from_db()
    return ballot


@pytest.mark.django_db
class TestFindRapidSuccessionPairs:
    def test_flags_gaps_under_five_seconds(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        _ballot_at(election, make_voter(student_number="1"), t0)
        _ballot_at(election, make_voter(student_number="2"), t0 + timedelta(seconds=2))
        _ballot_at(election, make_voter(student_number="3"), t0 + timedelta(seconds=12))

        pairs = find_rapid_succession_pairs(election)

        assert len(pairs) == 1
        assert pairs[0]["gap_seconds"] == 2.0
        assert set(pairs[0].keys()) == {"gap_seconds", "timestamp"}

    def test_empty_when_no_gaps_are_rapid(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        _ballot_at(election, make_voter(student_number="1"), t0)
        _ballot_at(election, make_voter(student_number="2"), t0 + timedelta(minutes=5))
        assert find_rapid_succession_pairs(election) == []

    def test_empty_with_zero_or_one_ballots(self, make_election, make_voter):
        election = make_election()
        assert find_rapid_succession_pairs(election) == []
        _ballot_at(election, make_voter(), timezone.now())
        assert find_rapid_succession_pairs(election) == []

    def test_no_voter_identifiers_in_output(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        voter = make_voter(student_number="SECRET-123")
        _ballot_at(election, voter, t0)
        _ballot_at(election, make_voter(student_number="2"), t0 + timedelta(seconds=1))
        pairs = find_rapid_succession_pairs(election)
        assert "SECRET-123" not in str(pairs)


@pytest.mark.django_db
class TestFindVelocityBursts:
    def test_flags_more_than_ten_ballots_in_sixty_seconds(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        for i in range(11):
            _ballot_at(
                election, make_voter(student_number=f"burst-{i}"), t0 + timedelta(seconds=i)
            )

        bursts = find_velocity_bursts(election)

        assert len(bursts) == 1
        assert bursts[0]["ballots_in_window"] == 11
        assert set(bursts[0].keys()) == {"window_end", "ballots_in_window"}

    def test_reports_one_entry_per_episode_not_per_sliding_position(
        self, make_election, make_voter
    ):
        election = make_election()
        t0 = timezone.now()
        # 12 ballots one second apart — the burst is sustained across many
        # window positions but should be reported once, not ~2 times.
        for i in range(12):
            _ballot_at(
                election, make_voter(student_number=f"sustained-{i}"), t0 + timedelta(seconds=i)
            )
        bursts = find_velocity_bursts(election)
        assert len(bursts) == 1

    def test_two_separate_episodes_both_reported(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        for i in range(11):
            _ballot_at(
                election, make_voter(student_number=f"a-{i}"), t0 + timedelta(seconds=i)
            )
        later = t0 + timedelta(minutes=10)
        for i in range(11):
            _ballot_at(
                election, make_voter(student_number=f"b-{i}"), later + timedelta(seconds=i)
            )
        bursts = find_velocity_bursts(election)
        assert len(bursts) == 2

    def test_empty_when_no_burst(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        for i in range(5):
            _ballot_at(
                election, make_voter(student_number=f"normal-{i}"), t0 + timedelta(seconds=i * 20)
            )
        assert find_velocity_bursts(election) == []

    def test_exactly_ten_does_not_trigger(self, make_election, make_voter):
        election = make_election()
        t0 = timezone.now()
        for i in range(10):
            _ballot_at(
                election, make_voter(student_number=f"ten-{i}"), t0 + timedelta(seconds=i)
            )
        assert find_velocity_bursts(election) == []
