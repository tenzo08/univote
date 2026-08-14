"""Demo data for a non-production instance only — see docs/06-DEPLOYMENT.md.
Never run against a real election database; every account this creates has
a known password.

--reset only ever touches @up.edu.ph accounts and Election rows (which
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

DEMO_EMAIL_DOMAIN = "@up.edu.ph"

# (first_name, last_name, local-part, student_number, year_level, degree_program)
ARCHIVED_CANDIDATES = [
    ("Andres", "Villanueva", "andres.villanueva", "2021-00521", "4", "BS Computer Science"),
    ("Carmela", "Reyes", "carmela.reyes", "2021-00734", "4", "BA Political Science"),
    ("Ramon", "Bautista", "ramon.bautista", "2020-01122", "4", "BS Civil Engineering"),
    ("Lourdes", "Aquino", "lourdes.aquino", "2020-00893", "4", "BS Biology"),
]
LIVE_CANDIDATES = [
    ("Diego", "Mercado", "diego.mercado", "2022-01340", "3", "BS Electrical Engineering"),
    ("Patricia", "Gonzales", "patricia.gonzales", "2022-00456", "3", "BS Psychology"),
    ("Joaquin", "Del Rosario", "joaquin.delrosario", "2021-01899", "3", "BS Accountancy"),
    ("Bianca", "Torres", "bianca.torres", "2021-02011", "3", "BA Broadcast Communication"),
    ("Emilio", "Cruz", "emilio.cruz", "2022-00987", "2", "BS Applied Mathematics"),
    ("Sofia", "Manalo", "sofia.manalo", "2022-01765", "2", "BS Statistics"),
]
GENERAL_ELECTORATE = [
    ("Rafael", "Domingo", "rafael.domingo", "2023-00234", "1", "BS Computer Science"),
    ("Angelica", "Pascual", "angelica.pascual", "2023-00567", "1", "BS Biology"),
    ("Marco", "Villareal", "marco.villareal", "2020-01456", "4", "BS Civil Engineering"),
    ("Nicole", "Sarmiento", "nicole.sarmiento", "2021-01023", "3", "BA Political Science"),
    ("Vicente", "Ocampo", "vicente.ocampo", "2022-00678", "2", "BS Electrical Engineering"),
    ("Katrina", "Salazar", "katrina.salazar", "2023-00891", "1", "BS Psychology"),
    ("Leandro", "Navarro", "leandro.navarro", "2020-00345", "4", "BS Accountancy"),
    ("Michaela", "Ignacio", "michaela.ignacio", "2021-01678", "3", "BS Applied Mathematics"),
]
# Left enrolled=False so the roster demonstrates the "not every voter is
# enrolled yet" state — a real, common admin-workflow moment, not a bug.
UNENROLLED_LOCAL_PARTS = {"leandro.navarro"}


class Command(BaseCommand):
    help = "Seed named @up.edu.ph accounts, three elections, a voter roster, and ballots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing @up.edu.ph accounts and all elections before seeding.",
        )

    def handle(self, *args, **options):
        already_seeded = (
            User.objects.filter(email__iendswith=DEMO_EMAIL_DOMAIN).exists()
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
        User.objects.filter(email__iendswith=DEMO_EMAIL_DOMAIN).delete()

    # -- account creation ---------------------------------------------------

    def _create_voter(
        self,
        first_name,
        last_name,
        local_part,
        student_number,
        year_level,
        degree_program,
        password=None,
        must_change_password=True,
    ):
        user = User.objects.create_user(
            email=f"{local_part}{DEMO_EMAIL_DOMAIN}",
            username=student_number,
            password=password or student_number,
            role=User.Role.VOTER,
            must_change_password=must_change_password,
            first_name=first_name,
            last_name=last_name,
        )
        return Voter.objects.create(
            user=user,
            student_number=student_number,
            year_level=year_level,
            degree_program=degree_program,
        )

    def _create_voters(self, entries):
        return [self._create_voter(*entry) for entry in entries]

    # -- election building ----------------------------------------------------

    def _build_election(self, title, opens_delta, closes_delta):
        now = timezone.now()
        return Election.objects.create(
            title=title, opens_at=now + opens_delta, closes_at=now + closes_delta
        )

    def _staff_positions_and_candidates(self, election, candidate_voters):
        president = add_position(election, title="President", max_votes=1, order=0)
        senator = add_position(election, title="Senator", max_votes=2, order=1)
        for voter in candidate_voters[:2]:
            register_candidate(election, president, voter.student_number)
        for voter in candidate_voters[2:]:
            register_candidate(election, senator, voter.student_number)
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
            email=f"isabel.fernandez{DEMO_EMAIL_DOMAIN}",
            username="isabel.fernandez",
            password="ComelecChair2026!",
            role=User.Role.ADMIN,
            first_name="Isabel",
            last_name="Fernandez",
        )
        User.objects.create_user(
            email=f"gabriel.santos{DEMO_EMAIL_DOMAIN}",
            username="gabriel.santos",
            password="USCAuditor2026!",
            role=User.Role.AUDITOR,
            first_name="Gabriel",
            last_name="Santos",
        )
        # The two accounts the deploy guide points people to first — both
        # frictionless (no forced password change), one already voted, one
        # enrolled but hasn't voted yet.
        already_voted = self._create_voter(
            "Ana",
            "Dela Cruz",
            "ana.delacruz",
            "2022-00120",
            "3",
            "BS Political Science",
            password="AnaVoter2026!",
            must_change_password=False,
        )
        not_yet_voted = self._create_voter(
            "Miguel",
            "Torres",
            "miguel.torres",
            "2021-00845",
            "4",
            "BS Biology",
            password="MiguelVoter2026!",
            must_change_password=False,
        )

        archived_candidates = self._create_voters(ARCHIVED_CANDIDATES)
        live_candidates = self._create_voters(LIVE_CANDIDATES)
        general_electorate = self._create_voters(GENERAL_ELECTORATE)

        archived_election = self._build_election(
            "General Election 2025",
            opens_delta=timedelta(days=-400),
            closes_delta=timedelta(days=-395),
        )
        self._staff_positions_and_candidates(archived_election, archived_candidates)
        publish_election(archived_election)

        live_election = self._build_election(
            "General Election 2026",
            opens_delta=timedelta(days=-3),
            closes_delta=timedelta(days=4),
        )
        president, senator = self._staff_positions_and_candidates(live_election, live_candidates)
        # Archives archived_election automatically — Election.publish()
        # archives every other published row by design.
        publish_election(live_election)

        self._build_election(
            "General Election 2027 (Planning)",
            opens_delta=timedelta(days=200),
            closes_delta=timedelta(days=203),
        )  # left as draft — next cycle, not yet staffed

        enrolled_electorate = [
            voter
            for voter, entry in zip(general_electorate, GENERAL_ELECTORATE)
            if entry[2] not in UNENROLLED_LOCAL_PARTS
        ]
        enroll(
            live_election,
            [voter.pk for voter in [already_voted, not_yet_voted] + enrolled_electorate],
        )

        voting_voters = live_candidates + enrolled_electorate + [already_voted]
        self._cast_staggered_ballots(live_election, voting_voters, president, senator)
