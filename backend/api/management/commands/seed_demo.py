"""Demo data for a non-production instance only — see docs/06-DEPLOYMENT.md.
Never run against a real election database; every account this creates has
a known password.

--reset only ever touches @test.com accounts and Election rows (which
cascade to positions/candidates/enrollments/ballots), so it's safe to run
right after `createsuperuser` on a fresh deploy without clobbering that
account."""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import Ballot, Election, User, Voter
from api.services.balloting import cast_ballot
from api.services.candidates import register_candidate
from api.services.elections import add_position, publish_election
from api.services.enrollment import enroll

DEMO_EMAIL_SUFFIX = "@test.com"
DEGREE_PROGRAMS = ["BS Computer Science", "BS Biology", "BS Psychology", "BS Accountancy"]
BULK_VOTER_COUNT = 63
# Reserved index ranges within the bulk voter pool — kept separate from the
# "leave some unenrolled" pool below so the two demo behaviors never fight
# over the same voters (a registered candidate is always auto-enrolled).
ARCHIVED_CANDIDATE_SLICE = slice(0, 6)
LIVE_CANDIDATE_SLICE = slice(6, 16)
UNENROLLED_EVERY_NTH = 7


class Command(BaseCommand):
    help = "Seed demo accounts, three elections, a voter roster, and staggered ballots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing @test.com accounts and all elections before seeding.",
        )

    def handle(self, *args, **options):
        already_seeded = (
            User.objects.filter(email__iendswith=DEMO_EMAIL_SUFFIX).exists()
            or Election.objects.exists()
        )
        if already_seeded and not options["reset"]:
            raise CommandError(
                "Database already has seed or election data — pass --reset to wipe "
                "and reseed. Refusing to run against a non-empty database otherwise."
            )
        if options["reset"]:
            self._reset()

        with transaction.atomic():
            self._seed()

        self.stdout.write(self.style.SUCCESS("Seed data created."))

    def _reset(self):
        Election.objects.all().delete()
        User.objects.filter(email__iendswith=DEMO_EMAIL_SUFFIX).delete()

    # -- account creation ---------------------------------------------------

    def _create_voter(self, email, student_number, password, must_change_password=True):
        user = User.objects.create_user(
            email=email,
            username=student_number,
            password=password,
            role=User.Role.VOTER,
            must_change_password=must_change_password,
        )
        return Voter.objects.create(
            user=user,
            student_number=student_number,
            year_level=random.choice(["1", "2", "3", "4"]),
            degree_program=random.choice(DEGREE_PROGRAMS),
        )

    # -- election building ----------------------------------------------------

    def _build_election(self, title, opens_delta, closes_delta):
        now = timezone.now()
        return Election.objects.create(
            title=title, opens_at=now + opens_delta, closes_at=now + closes_delta
        )

    def _staff_positions_and_candidates(self, election, candidate_voters, extra_voter=None):
        president = add_position(election, title="President", max_votes=1, order=0)
        senator = add_position(election, title="Senator", max_votes=2, order=1)
        pool = list(candidate_voters)
        for voter in pool[:2]:
            register_candidate(election, president, voter.student_number)
        for voter in pool[2:]:
            register_candidate(election, senator, voter.student_number)
        if extra_voter is not None:
            register_candidate(election, president, extra_voter.student_number)
        return president, senator

    # -- ballots ---------------------------------------------------------------

    def _stagger_gaps(self, count):
        """count-1 gaps in seconds. The first is forced under 5s (rapid
        succession) and the second is forced over an hour (a multi-hour
        jump) so the timeline/integrity-report demo always has real shape
        to show, regardless of what the rest of the random spacing does."""
        forced = [2.0, 4 * 3600]
        rest = [random.uniform(30, 480) for _ in range(max(0, count - 1 - len(forced)))]
        random.shuffle(rest)
        return forced + rest

    def _cast_staggered_ballots(self, election, voters, president, senator):
        president_candidate_ids = list(president.candidates.values_list("id", flat=True))
        senator_candidate_ids = list(senator.candidates.values_list("id", flat=True))

        ballots = []
        for voter in voters:
            selections = []
            if president_candidate_ids:
                selections.append(
                    {
                        "position_id": president.id,
                        "candidate_ids": [random.choice(president_candidate_ids)],
                    }
                )
            if senator_candidate_ids:
                k = random.randint(1, min(2, len(senator_candidate_ids)))
                selections.append(
                    {
                        "position_id": senator.id,
                        "candidate_ids": random.sample(senator_candidate_ids, k),
                    }
                )
            ballots.append(cast_ballot(voter, election, selections))

        base = election.opens_at + timedelta(hours=2)
        gaps = self._stagger_gaps(len(ballots))
        timestamp = base
        for ballot, gap in zip(ballots, [0] + gaps):
            timestamp += timedelta(seconds=gap)
            Ballot.objects.filter(pk=ballot.pk).update(submitted_at=timestamp)

    # -- top-level assembly -----------------------------------------------------

    def _seed(self):
        User.objects.create_superuser(
            email="admin@test.com",
            username="admin",
            password="DemoAdmin123!",
            role=User.Role.ADMIN,
        )
        User.objects.create_user(
            email="auditor@test.com",
            username="auditor",
            password="DemoAuditor123!",
            role=User.Role.AUDITOR,
        )
        sample_voter = self._create_voter(
            "voter@test.com", "sample-voter", "DemoVoter123!", must_change_password=False
        )
        sample_candidate_voter = self._create_voter(
            "candidate@test.com",
            "sample-candidate",
            "DemoCandidate123!",
            must_change_password=False,
        )
        bulk_voters = [
            self._create_voter(f"bulkvoter{i}@test.com", f"bulk-{i:04d}", f"bulk-{i:04d}")
            for i in range(BULK_VOTER_COUNT)
        ]

        archived_election = self._build_election(
            "General Election 2025",
            opens_delta=timedelta(days=-400),
            closes_delta=timedelta(days=-395),
        )
        self._staff_positions_and_candidates(
            archived_election, bulk_voters[ARCHIVED_CANDIDATE_SLICE]
        )
        publish_election(archived_election)

        live_election = self._build_election(
            "General Election 2026",
            opens_delta=timedelta(days=-3),
            closes_delta=timedelta(days=4),
        )
        president, senator = self._staff_positions_and_candidates(
            live_election, bulk_voters[LIVE_CANDIDATE_SLICE], extra_voter=sample_candidate_voter
        )
        # Archives archived_election automatically — Election.publish()
        # archives every other published row by design.
        publish_election(live_election)

        self._build_election(
            "General Election 2027 (Planning)",
            opens_delta=timedelta(days=200),
            closes_delta=timedelta(days=203),
        )  # left as draft — next cycle, not yet staffed

        remaining_pool = bulk_voters[16:]
        enroll(live_election, [sample_voter.pk])
        to_enroll = [
            voter.pk
            for i, voter in enumerate(remaining_pool)
            if i % UNENROLLED_EVERY_NTH != 0
        ]
        enroll(live_election, to_enroll)

        to_enroll_set = set(to_enroll)
        voting_voters = list(bulk_voters[LIVE_CANDIDATE_SLICE]) + [
            v for v in remaining_pool if v.pk in to_enroll_set
        ][:30]
        self._cast_staggered_ballots(live_election, voting_voters, president, senator)
