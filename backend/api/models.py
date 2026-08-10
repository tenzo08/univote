import secrets

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager required because USERNAME_FIELD is "email" but
    AbstractUser's default manager assumes the natural identity field is
    "username" — without this, createsuperuser and programmatic user
    creation get a positional-argument mismatch."""

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address.")
        if not username:
            raise ValueError("User must have a username.")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        VOTER = "voter", "Voter"
        AUDITOR = "auditor", "Auditor"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VOTER)
    must_change_password = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def __str__(self):
        return self.email


class Voter(models.Model):
    """Profile data for role == "voter". student_number is the identity
    anchor everywhere — never match voters by name."""

    user = models.OneToOneField(
        User, related_name="voter_profile", on_delete=models.CASCADE
    )
    student_number = models.CharField(max_length=32, unique=True)
    year_level = models.CharField(max_length=32)
    degree_program = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.student_number} ({self.user.email})"


class Election(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(closes_at__gt=models.F("opens_at")),
                name="election_closes_after_opens",
            ),
            # The real defence against two elections being published at once
            # under concurrent publish() calls — same reasoning as Ballot's
            # unique_together being "the real defence" against double voting.
            # A partial unique index on status='published' means the loser of
            # a race gets IntegrityError on save(), not a silently-corrupted
            # two-published-elections state. Supported on both Postgres and
            # SQLite (this project's two DB backends).
            models.UniqueConstraint(
                fields=["status"],
                condition=models.Q(status="published"),
                name="only_one_published_election",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_open_for_voting(self):
        now = timezone.now()
        return (
            self.status == self.Status.PUBLISHED
            and self.opens_at <= now <= self.closes_at
        )

    def publish(self):
        """Archives every other published election, sets status=published
        and published_at=now. This is the one-published-election invariant —
        it lives on the model so it can't be skipped by calling a view
        directly."""
        with transaction.atomic():
            Election.objects.filter(status=self.Status.PUBLISHED).exclude(
                pk=self.pk
            ).update(status=self.Status.ARCHIVED)
            self.status = self.Status.PUBLISHED
            self.published_at = timezone.now()
            self.save(update_fields=["status", "published_at"])


class Position(models.Model):
    election = models.ForeignKey(
        Election, related_name="positions", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=128)
    max_votes = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("election", "title")
        ordering = ["order", "id"]
        constraints = [
            # PositiveIntegerField allows 0 despite the name; max_votes=0
            # would be a seat nobody could ever fill.
            models.CheckConstraint(
                condition=models.Q(max_votes__gte=1),
                name="position_max_votes_at_least_one",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.election.title})"


class Candidate(models.Model):
    election = models.ForeignKey(
        Election, related_name="candidates", on_delete=models.CASCADE
    )
    position = models.ForeignKey(
        Position, related_name="candidates", on_delete=models.CASCADE
    )
    voter = models.ForeignKey(
        Voter, related_name="candidacies", on_delete=models.CASCADE
    )
    platform = models.TextField(blank=True)
    photo = models.ImageField(upload_to="candidates/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("election", "voter", "position")

    def __str__(self):
        return f"{self.voter.student_number} for {self.position.title}"

    def clean(self):
        """A position.election / candidate.election mismatch would corrupt
        tallies silently."""
        super().clean()
        if (
            self.position_id
            and self.election_id
            and self.position.election_id != self.election_id
        ):
            raise ValidationError(
                "Candidate's position must belong to the same election as "
                "the candidate."
            )

    def save(self, *args, **kwargs):
        # clean() (not full_clean()) so this enforces only the cross-election
        # check on every save path — ORM, admin, services alike — without
        # duplicating validate_unique()'s job; the DB unique_together above
        # is still what actually raises IntegrityError for duplicates.
        self.clean()
        super().save(*args, **kwargs)


class ElectionEnrollment(models.Model):
    """The voter roster. Eligibility is explicit; no implicit "all voters
    can vote"."""

    election = models.ForeignKey(
        Election, related_name="enrollments", on_delete=models.CASCADE
    )
    voter = models.ForeignKey(
        Voter, related_name="enrollments", on_delete=models.CASCADE
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("election", "voter")

    def __str__(self):
        return f"{self.voter.student_number} enrolled in {self.election.title}"


class Ballot(models.Model):
    """One per voter per election. unique_together is the real defence
    against double voting — the application check is a courtesy that
    produces a nice error message; this constraint is what actually holds
    under a race condition."""

    election = models.ForeignKey(
        Election, related_name="ballots", on_delete=models.CASCADE
    )
    voter = models.ForeignKey(Voter, related_name="ballots", on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    receipt_code = models.CharField(max_length=16, unique=True, editable=False)

    class Meta:
        unique_together = ("election", "voter")
        ordering = ["submitted_at"]

    def __str__(self):
        return f"Ballot {self.receipt_code}"

    def save(self, *args, **kwargs):
        if not self.receipt_code:
            self.receipt_code = secrets.token_hex(8)
        super().save(*args, **kwargs)


class BallotSelection(models.Model):
    """One row per candidate chosen. Multiple rows per position when
    max_votes > 1. Storing selections as rows (rather than a JSON blob)
    means tallying is a GROUP BY the database does well."""

    ballot = models.ForeignKey(
        Ballot, related_name="selections", on_delete=models.CASCADE
    )
    position = models.ForeignKey(
        Position, related_name="selections", on_delete=models.CASCADE
    )
    candidate = models.ForeignKey(
        Candidate, related_name="selections", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("ballot", "position", "candidate")

    def __str__(self):
        return f"{self.ballot_id}: {self.candidate_id} for {self.position_id}"

    def clean(self):
        """BallotSelection is what tallying actually GROUP BYs — a selection
        pointing at a candidate from the wrong position or a different
        election than the ballot would corrupt the tally the same way an
        unchecked Candidate mismatch would."""
        super().clean()
        if self.candidate_id and self.position_id:
            if self.candidate.position_id != self.position_id:
                raise ValidationError(
                    "Selected candidate does not belong to this position."
                )
        if self.candidate_id and self.ballot_id:
            if self.candidate.election_id != self.ballot.election_id:
                raise ValidationError(
                    "Selected candidate does not belong to this ballot's election."
                )
        if self.position_id and self.ballot_id:
            if self.position.election_id != self.ballot.election_id:
                raise ValidationError(
                    "Selected position does not belong to this ballot's election."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
