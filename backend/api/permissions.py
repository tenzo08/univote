"""Defined once, applied per-view. Never inline a role check in a view
body. DRF's default is IsAuthenticated — nothing in this project is
public except login and refresh."""

from rest_framework.permissions import BasePermission

from api.models import User


class _RoleBasePermission(BasePermission):
    """A single place to change what "authenticated" means for every role
    check — a future addition (e.g. an is_active/suspended check) only
    needs to change here, not in four separately-copy-pasted places."""

    def _authenticated_user(self, request):
        user = request.user
        if user and user.is_authenticated:
            return user
        return None


class IsAdmin(_RoleBasePermission):
    def has_permission(self, request, view):
        user = self._authenticated_user(request)
        return bool(user and user.role == User.Role.ADMIN)


class IsAuditorOrAdmin(_RoleBasePermission):
    def has_permission(self, request, view):
        user = self._authenticated_user(request)
        return bool(user and user.role in (User.Role.AUDITOR, User.Role.ADMIN))


class IsVoter(_RoleBasePermission):
    def has_permission(self, request, view):
        user = self._authenticated_user(request)
        return bool(user and user.role == User.Role.VOTER)


class CanCastBallot(_RoleBasePermission):
    def has_permission(self, request, view):
        user = self._authenticated_user(request)
        return bool(user and user.role == User.Role.VOTER and not user.must_change_password)
