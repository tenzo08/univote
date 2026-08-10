from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from api.models import User, Voter


def _full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role/must_change_password/full_name/user_id to the login
    response body — not to the JWT payload itself. request.user is
    re-fetched from the DB on every authenticated request, so embedding
    these in the token would be pure duplication that could go stale."""

    def validate(self, attrs):
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
    new_password = serializers.CharField(write_only=True)
