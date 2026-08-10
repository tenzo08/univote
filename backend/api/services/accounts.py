"""Account-level actions that are more than field validation: changing a
password is a decision (was this password ever the voter's own student
number?) plus a mutation (clear must_change_password), so — same pattern as
cast_ballot() — both live together here, not split across a serializer and
a view."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def change_password(user, new_password):
    """Raises django.core.exceptions.ValidationError (a list of messages)
    on failure. On success, saves the user with the new password and
    must_change_password cleared."""
    # Checked before Django's validators (not after): CSV-imported voters
    # have username == student_number, so UserAttributeSimilarityValidator
    # would otherwise catch this first with a confusing "too similar to
    # username" message — voters don't think of their login as having a
    # username. This only catches an exact (case-insensitive) match; a
    # near-miss like the student number with a character added or removed
    # still falls through to Django's validator and its less specific
    # message — an accepted limitation, not a correctness gap (the
    # near-miss password is still correctly rejected either way).
    voter_profile = getattr(user, "voter_profile", None)
    if voter_profile is not None and new_password.lower() == voter_profile.student_number.lower():
        raise ValidationError("You can't reuse your student number as your password.")

    validate_password(new_password, user=user)

    user.set_password(new_password)
    user.must_change_password = False
    user.save()
