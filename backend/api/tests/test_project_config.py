"""Project-wiring assertions that don't belong to any single domain test
file — settings, middleware ordering, etc. Split out of test_auth.py, which
should stay auth-only per 01-ARCHITECTURE.md's test layout."""


class TestCorsWiring:
    def test_cors_middleware_precedes_whitenoise(self, settings):
        cors_index = settings.MIDDLEWARE.index("corsheaders.middleware.CorsMiddleware")
        whitenoise_index = settings.MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware")
        assert cors_index < whitenoise_index

    def test_cors_allowed_origins_reads_from_settings(self, settings):
        assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
