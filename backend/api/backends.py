"""Case-insensitive email authentication. CSV-imported voter emails are
stored with their original casing (only the domain part is lowercased by
Django's normalize_email), and duplicate detection during import is already
case-insensitive (email__iexact) — but the stock ModelBackend does an exact
match on USERNAME_FIELD, so a voter typing their email in different case
than the roster CSV had it would get the generic 401, indistinguishable
from a wrong password."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailCaseInsensitiveBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None
        try:
            user = UserModel._default_manager.get(
                **{f"{UserModel.USERNAME_FIELD}__iexact": username}
            )
        except UserModel.DoesNotExist:
            # Run the hasher anyway — same timing-attack mitigation Django's
            # own ModelBackend uses for a nonexistent user.
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
