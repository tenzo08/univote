import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from api.models import User
from api.permissions import CanCastBallot, IsAdmin, IsAuditorOrAdmin, IsVoter


def _request_for(user):
    django_request = APIRequestFactory().get("/")
    request = Request(django_request)
    request.user = user
    return request


@pytest.mark.django_db
class TestPermissions:
    def test_is_admin(self, make_user):
        admin = make_user(email="a@test.com", role=User.Role.ADMIN)
        voter = make_user(email="v@test.com", role=User.Role.VOTER)
        auditor = make_user(email="au@test.com", role=User.Role.AUDITOR)
        perm = IsAdmin()
        assert perm.has_permission(_request_for(admin), None) is True
        assert perm.has_permission(_request_for(voter), None) is False
        assert perm.has_permission(_request_for(auditor), None) is False
        assert perm.has_permission(_request_for(AnonymousUser()), None) is False

    def test_is_auditor_or_admin(self, make_user):
        admin = make_user(email="a2@test.com", role=User.Role.ADMIN)
        auditor = make_user(email="au2@test.com", role=User.Role.AUDITOR)
        voter = make_user(email="v2@test.com", role=User.Role.VOTER)
        perm = IsAuditorOrAdmin()
        assert perm.has_permission(_request_for(admin), None) is True
        assert perm.has_permission(_request_for(auditor), None) is True
        assert perm.has_permission(_request_for(voter), None) is False
        assert perm.has_permission(_request_for(AnonymousUser()), None) is False

    def test_is_voter(self, make_user):
        voter = make_user(email="v3@test.com", role=User.Role.VOTER)
        admin = make_user(email="a3@test.com", role=User.Role.ADMIN)
        auditor = make_user(email="au3@test.com", role=User.Role.AUDITOR)
        perm = IsVoter()
        assert perm.has_permission(_request_for(voter), None) is True
        assert perm.has_permission(_request_for(admin), None) is False
        assert perm.has_permission(_request_for(auditor), None) is False

    def test_can_cast_ballot(self, make_user):
        eligible = make_user(email="e@test.com", role=User.Role.VOTER, must_change_password=False)
        must_change = make_user(email="m@test.com", role=User.Role.VOTER, must_change_password=True)
        admin = make_user(email="a4@test.com", role=User.Role.ADMIN)
        perm = CanCastBallot()
        assert perm.has_permission(_request_for(eligible), None) is True
        assert perm.has_permission(_request_for(must_change), None) is False
        assert perm.has_permission(_request_for(admin), None) is False
        assert perm.has_permission(_request_for(AnonymousUser()), None) is False


@pytest.mark.django_db
class TestLogin:
    def test_happy_path_returns_expected_shape(self, make_user):
        user = make_user(
            email="login@up.edu.ph", role=User.Role.VOTER, first_name="Ana", last_name="Santos"
        )
        response = APIClient().post(
            "/api/auth/login/",
            {"email": "login@up.edu.ph", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "voter"
        assert data["must_change_password"] is False
        assert data["full_name"] == "Ana Santos"
        assert data["user_id"] == user.id
        assert "access" in data and "refresh" in data

    def test_wrong_password_and_unknown_email_return_identical_message(self, make_user):
        make_user(email="known@test.com")
        client = APIClient()
        wrong_password = client.post(
            "/api/auth/login/", {"email": "known@test.com", "password": "wrong"}, format="json"
        )
        unknown_email = client.post(
            "/api/auth/login/", {"email": "nobody@test.com", "password": "whatever"}, format="json"
        )
        assert wrong_password.status_code == 401
        assert unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()

    def test_non_up_edu_ph_email_is_rejected_even_with_correct_password(self, make_user):
        # Domain restriction fires before authenticate() ever runs, so a
        # real account outside the required domain is rejected the exact
        # same way as a wrong password — no signal that the domain check
        # exists at all.
        make_user(email="outsider@gmail.com")
        client = APIClient()
        outsider = client.post(
            "/api/auth/login/",
            {"email": "outsider@gmail.com", "password": "testpass123"},
            format="json",
        )
        unknown_email = client.post(
            "/api/auth/login/", {"email": "nobody@up.edu.ph", "password": "whatever"}, format="json"
        )
        assert outsider.status_code == 401
        assert unknown_email.status_code == 401
        assert outsider.json() == unknown_email.json()

    def test_domain_check_is_case_insensitive(self, make_user):
        make_user(email="caps@Up.Edu.Ph")
        response = APIClient().post(
            "/api/auth/login/",
            {"email": "caps@Up.Edu.Ph", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200

    def test_login_is_case_insensitive_on_email(self, make_user):
        # CSV-imported voter emails keep their original casing; a voter
        # typing a different case than the roster had must still log in.
        make_user(email="Ana.Santos@Up.Edu.Ph")
        response = APIClient().post(
            "/api/auth/login/",
            {"email": "ana.santos@up.edu.ph", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200

    def test_must_change_password_voter_can_still_log_in(self, make_user):
        make_user(email="mustchange@up.edu.ph", must_change_password=True)
        response = APIClient().post(
            "/api/auth/login/",
            {"email": "mustchange@up.edu.ph", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["must_change_password"] is True


@pytest.mark.django_db
class TestRefresh:
    def test_valid_refresh_token_returns_new_access_token(self, make_user):
        make_user(email="refresh@up.edu.ph")
        client = APIClient()
        login = client.post(
            "/api/auth/login/", {"email": "refresh@up.edu.ph", "password": "testpass123"}, format="json"
        )
        response = client.post("/api/auth/refresh/", {"refresh": login.json()["refresh"]}, format="json")
        assert response.status_code == 200
        assert "access" in response.json()


@pytest.mark.django_db
class TestMe:
    def test_requires_authentication(self):
        response = APIClient().get("/api/me/")
        assert response.status_code == 401

    def test_voter_includes_nested_voter_object(self, make_voter):
        voter = make_voter(student_number="ME-1")
        client = APIClient()
        client.force_authenticate(user=voter.user)
        response = client.get("/api/me/")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "voter"
        assert data["voter"]["student_number"] == "ME-1"

    def test_admin_has_null_voter(self, make_user):
        admin = make_user(email="admin-me@test.com", role=User.Role.ADMIN)
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get("/api/me/")
        assert response.json()["voter"] is None


@pytest.mark.django_db
class TestChangePassword:
    def test_requires_authentication(self):
        response = APIClient().post("/api/change-password/", {"new_password": "whatever123"}, format="json")
        assert response.status_code == 401

    def test_success_clears_flag_and_new_password_works(self, make_user):
        user = make_user(email="cp@up.edu.ph", must_change_password=True)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/change-password/",
            {"current_password": "testpass123", "new_password": "a-strong-new-pw-99"},
            format="json",
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.must_change_password is False

        login = APIClient().post(
            "/api/auth/login/", {"email": "cp@up.edu.ph", "password": "a-strong-new-pw-99"}, format="json"
        )
        assert login.status_code == 200

    def test_rejects_wrong_current_password(self, make_user):
        user = make_user(email="cp-wrong@test.com", must_change_password=True)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/change-password/",
            {"current_password": "not-the-real-password", "new_password": "a-strong-new-pw-99"},
            format="json",
        )
        assert response.status_code == 400
        assert "current password" in str(response.json()).lower()
        user.refresh_from_db()
        assert user.must_change_password is True
        assert user.check_password("testpass123")

    def test_rejects_password_that_fails_django_validators(self, make_user):
        user = make_user(email="cp2@test.com")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/change-password/",
            {"current_password": "testpass123", "new_password": "short"},
            format="json",
        )
        assert response.status_code == 400
        assert "new_password" in response.json()

    def test_rejects_reusing_student_number(self, make_voter):
        voter = make_voter(student_number="2021-55555")
        client = APIClient()
        client.force_authenticate(user=voter.user)
        response = client.post(
            "/api/change-password/",
            {"current_password": "testpass123", "new_password": "2021-55555"},
            format="json",
        )
        assert response.status_code == 400
        assert "student number" in str(response.json())

    def test_does_not_wrongly_block_admin_without_voter_profile(self, make_user):
        admin = make_user(email="cp3@test.com", role=User.Role.ADMIN)
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(
            "/api/change-password/",
            {"current_password": "testpass123", "new_password": "a-fine-admin-password-1"},
            format="json",
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestLoginThrottling:
    def test_login_is_rate_limited(self, monkeypatch):
        from django.core.cache import cache as django_cache

        from api.throttling import LoginRateThrottle

        # SimpleRateThrottle.THROTTLE_RATES is a class attribute captured
        # from api_settings at import time — overriding settings.REST_
        # FRAMEWORK at test-time doesn't reach it, so the class attribute
        # itself is monkeypatched instead.
        monkeypatch.setattr(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"})
        django_cache.clear()
        client = APIClient()
        try:
            for _ in range(3):
                response = client.post(
                    "/api/auth/login/",
                    {"email": "nobody@test.com", "password": "x"},
                    format="json",
                )
                assert response.status_code == 401
            response = client.post(
                "/api/auth/login/", {"email": "nobody@test.com", "password": "x"}, format="json"
            )
            assert response.status_code == 429
        finally:
            django_cache.clear()
