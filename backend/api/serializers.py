from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from api.models import Candidate, Election, Position, User, Voter


def _full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role/must_change_password/full_name/user_id to the login
    response body — not to the JWT payload itself. request.user is
    re-fetched from the DB on every authenticated request, so embedding
    these in the token would be pure duplication that could go stale."""

    def validate(self, attrs):
        email = attrs.get(self.username_field, "")
        required_domain = settings.REQUIRED_LOGIN_EMAIL_DOMAIN
        if required_domain and not email.lower().endswith(f"@{required_domain.lower()}"):
            # Same exception, same message SimpleJWT itself raises for a
            # wrong password or unknown email — indistinguishable, so this
            # never reveals that a domain restriction exists at all. Also
            # run the password hasher on a throwaway user first (the same
            # dummy-hash technique EmailCaseInsensitiveBackend uses for an
            # unknown account) so this branch takes comparably long to the
            # real authentication path — otherwise it returns near-instantly
            # while a wrong-password/unknown-email attempt pays the full
            # hasher cost, and that latency gap is itself a signal an
            # attacker could use to detect the domain restriction exists.
            User().set_password(attrs.get("password", ""))
            raise AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["must_change_password"] = self.user.must_change_password
        data["full_name"] = _full_name(self.user)
        data["user_id"] = self.user.id
        return data


class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = ["student_number", "year_level", "degree_program"]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    voter = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "full_name", "must_change_password", "voter"]

    def get_full_name(self, obj):
        return _full_name(obj)

    def get_voter(self, obj):
        voter_profile = getattr(obj, "voter_profile", None)
        if voter_profile is None:
            return None
        return VoterSerializer(voter_profile).data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


# --- Elections ---------------------------------------------------------------


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "title", "max_votes", "order"]


class PositionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["title", "max_votes", "order"]


class ElectionSerializer(serializers.ModelSerializer):
    """Read side. Relies on the view annotating candidate_count/
    enrolled_count/ballot_count on every queryset it uses — these fields
    read straight off the annotated instance, they aren't computed here."""

    positions = PositionSerializer(many=True, read_only=True)
    candidate_count = serializers.IntegerField(read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    ballot_count = serializers.IntegerField(read_only=True)
    is_open_for_voting = serializers.BooleanField(read_only=True)

    class Meta:
        model = Election
        fields = [
            "id",
            "title",
            "description",
            "status",
            "opens_at",
            "closes_at",
            "published_at",
            "created_at",
            "candidate_count",
            "enrolled_count",
            "ballot_count",
            "is_open_for_voting",
            "positions",
        ]


class ElectionWriteSerializer(serializers.ModelSerializer):
    """POST accepts nested positions so an election is created in one round
    trip. PATCH reuses this serializer in partial mode; positions (if sent)
    are silently ignored on update — spec restricts PATCH to
    title/description/opens_at/closes_at, positions are only ever added via
    the dedicated add-position endpoint."""

    positions = PositionWriteSerializer(many=True, required=False)

    class Meta:
        model = Election
        fields = ["id", "title", "description", "opens_at", "closes_at", "positions"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        opens_at = attrs.get("opens_at", getattr(self.instance, "opens_at", None))
        closes_at = attrs.get("closes_at", getattr(self.instance, "closes_at", None))
        if opens_at and closes_at and closes_at <= opens_at:
            raise serializers.ValidationError(
                {"closes_at": "Must be after opens_at."}
            )
        positions = attrs.get("positions")
        if positions:
            titles = [p["title"] for p in positions]
            if len(titles) != len(set(titles)):
                raise serializers.ValidationError(
                    {"positions": "Position titles must be unique within an election."}
                )
        return attrs

    def create(self, validated_data):
        positions_data = validated_data.pop("positions", [])
        with transaction.atomic():
            election = Election.objects.create(**validated_data)
            for position_data in positions_data:
                Position.objects.create(election=election, **position_data)
        return election

class AddPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "title", "max_votes", "order"]
        read_only_fields = ["id"]


# --- Candidates ----------------------------------------------------------------


class CandidateSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    student_number = serializers.CharField(source="voter.student_number", read_only=True)
    position = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Candidate
        fields = ["id", "position", "full_name", "student_number", "platform", "photo"]

    def get_full_name(self, obj):
        return _full_name(obj.voter.user)


class CandidateRegisterSerializer(serializers.Serializer):
    """Identity is the student number, never first/last name. position/
    election match is plain field validation, so it lives here rather than
    the service — register_candidate() owns the decisions (voter
    resolution, auto-enrollment, published-election lock)."""

    student_number = serializers.CharField()
    position = serializers.PrimaryKeyRelatedField(queryset=Position.objects.all())
    platform = serializers.CharField(required=False, allow_blank=True, default="")
    photo = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        election = self.context["election"]
        if attrs["position"].election_id != election.id:
            raise serializers.ValidationError(
                {"position": "This position does not belong to this election."}
            )
        return attrs


class CandidateUpdateSerializer(serializers.ModelSerializer):
    """Platform and photo only — never the voter or the position. Plain
    field mutation, no service function needed."""

    class Meta:
        model = Candidate
        fields = ["platform", "photo"]


# --- Voting --------------------------------------------------------------------


class CastBallotSelectionSerializer(serializers.Serializer):
    """Shape validation only — position/candidate ownership, max_votes, and
    duplicate checks are cast_ballot()'s job (services/balloting.py), which
    already implements the exact 8-step order 03-API-SPEC.md specifies."""

    position_id = serializers.IntegerField()
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, default=list
    )


class CastBallotSerializer(serializers.Serializer):
    selections = CastBallotSelectionSerializer(many=True)
