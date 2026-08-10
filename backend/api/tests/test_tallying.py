import pytest

from api.models import Ballot, BallotSelection
from api.services.tallying import (
    compute_results,
    compute_turnout,
    compute_turnout_breakdown,
)


def _cast(election, voter, position, candidates):
    """Directly creates a Ballot + BallotSelection rows, bypassing the
    balloting service — tallying must work regardless of how a ballot was
    recorded, including on closed/archived elections cast_ballot() would
    itself refuse."""
    ballot, _ = Ballot.objects.get_or_create(election=election, voter=voter)
    for candidate in candidates:
        BallotSelection.objects.create(ballot=ballot, position=position, candidate=candidate)
    return ballot


@pytest.mark.django_db
class TestComputeResults:
    def test_hand_computed_exact_vote_counts_and_tie_detection(
        self, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election()
        president = make_position(election=election, title="President", max_votes=1)
        senator = make_position(election=election, title="Senator", max_votes=2)

        a = make_candidate(election=election, position=president, voter=make_voter(student_number="A"))
        b = make_candidate(election=election, position=president, voter=make_voter(student_number="B"))
        c = make_candidate(election=election, position=senator, voter=make_voter(student_number="C"))
        d = make_candidate(election=election, position=senator, voter=make_voter(student_number="D"))
        e = make_candidate(election=election, position=senator, voter=make_voter(student_number="E"))

        v1, v2, v3, v4 = (make_voter(student_number=f"V{i}") for i in range(1, 5))

        # President: A gets 2 votes (v1, v2), B gets 1 (v3) — v4 undervotes.
        _cast(election, v1, president, [a])
        _cast(election, v2, president, [a])
        _cast(election, v3, president, [b])
        # v4 casts no President selection but does vote Senator (below) —
        # get_or_create in _cast() means v4's Ballot exists either way.

        # Senator: C=3 (v1,v2,v3), D=2 (v1,v4), E=2 (v2,v4) — tie for the
        # second seat between D and E.
        _cast(election, v1, senator, [c, d])
        _cast(election, v2, senator, [c, e])
        _cast(election, v3, senator, [c])
        _cast(election, v4, senator, [d, e])

        results = compute_results(election)
        by_position = {r["position"]: r for r in results}

        president_result = by_position["President"]
        assert president_result["max_votes"] == 1
        assert president_result["is_tied"] is False
        votes_by_candidate = {c["candidate_id"]: c["votes"] for c in president_result["candidates"]}
        assert votes_by_candidate == {a.id: 2, b.id: 1}
        assert president_result["candidates"][0]["candidate_id"] == a.id

        senator_result = by_position["Senator"]
        assert senator_result["max_votes"] == 2
        assert senator_result["is_tied"] is True
        votes_by_candidate = {c["candidate_id"]: c["votes"] for c in senator_result["candidates"]}
        assert votes_by_candidate == {c.id: 3, d.id: 2, e.id: 2}

    def test_no_tie_when_candidate_count_does_not_exceed_max_votes(
        self, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election()
        position = make_position(election=election, title="Senator", max_votes=3)
        make_candidate(election=election, position=position, voter=make_voter(student_number="X"))
        make_candidate(election=election, position=position, voter=make_voter(student_number="Y"))
        # Only 2 candidates for 3 seats — no boundary to be tied at.
        results = compute_results(election)
        assert results[0]["is_tied"] is False

    def test_uses_full_name_when_present_else_student_number(
        self, make_election, make_position, make_candidate, make_voter
    ):
        election = make_election()
        position = make_position(election=election)
        voter = make_voter(student_number="NONAME")
        make_candidate(election=election, position=position, voter=voter)
        result = compute_results(election)[0]
        assert result["candidates"][0]["name"] == "NONAME"


@pytest.mark.django_db
class TestComputeTurnout:
    def test_zero_percent_when_nobody_enrolled(self, make_election):
        election = make_election()
        turnout = compute_turnout(election)
        assert turnout == {"enrolled": 0, "voted": 0, "turnout_pct": 0}

    def test_exact_percentage(self, make_election, make_voter, make_enrollment, make_ballot):
        election = make_election()
        voters = [make_voter(student_number=f"T{i}") for i in range(5)]
        for voter in voters:
            make_enrollment(election, voter)
        for voter in voters[:4]:
            make_ballot(election, voter)

        turnout = compute_turnout(election)
        assert turnout == {"enrolled": 5, "voted": 4, "turnout_pct": 80.0}


@pytest.mark.django_db
class TestComputeTurnoutBreakdown:
    def test_small_groups_merge_into_other(self, make_election, make_voter, make_enrollment, make_ballot):
        election = make_election()
        # 6 voters in "BS Computer Science" (>=5, kept as its own group,
        # 3 of whom vote), 2 voters in "BS Biology" (<5, suppressed).
        cs_voters = [
            make_voter(student_number=f"CS{i}", degree_program="BS Computer Science", year_level="1")
            for i in range(6)
        ]
        bio_voters = [
            make_voter(student_number=f"BIO{i}", degree_program="BS Biology", year_level="1")
            for i in range(2)
        ]
        for voter in cs_voters + bio_voters:
            make_enrollment(election, voter)
        for voter in cs_voters[:3]:
            make_ballot(election, voter)
        make_ballot(election, bio_voters[0])

        breakdown = compute_turnout_breakdown(election)
        by_program = {g["group"]: g for g in breakdown["by_degree_program"]}

        assert by_program["BS Computer Science"] == {
            "group": "BS Computer Science",
            "enrolled": 6,
            "voted": 3,
        }
        assert by_program["Other"] == {"group": "Other", "enrolled": 2, "voted": 1}

        # All voters share year_level="1" here — 8 enrolled is >= threshold,
        # stays its own group rather than folding into Other.
        by_year = {g["group"]: g for g in breakdown["by_year_level"]}
        assert by_year["1"] == {"group": "1", "enrolled": 8, "voted": 4}

    def test_empty_when_nobody_enrolled(self, make_election):
        election = make_election()
        breakdown = compute_turnout_breakdown(election)
        assert breakdown == {"by_year_level": [], "by_degree_program": []}
