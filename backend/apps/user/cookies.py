from django.conf import settings

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def _cookie_flags():
    # The frontends (Vercel) and this API (Render/VPS domain) are on different
    # registrable domains - a genuinely cross-site setup. SameSite=Lax cookies
    # are never attached to a fetch()/XHR request across sites (only to
    # top-level navigations), so the browser would silently drop them on
    # every API call after login. SameSite=None fixes that, but browsers
    # require Secure with it, which needs HTTPS - fine in production, but
    # unusable for plain-HTTP local dev, hence the DEBUG branch.
    secure = not settings.DEBUG
    samesite = "None" if secure else "Lax"
    return secure, samesite


def set_auth_cookies(response, access: str, refresh: str | None = None):
    secure, samesite = _cookie_flags()
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
    )
    if refresh is not None:
        response.set_cookie(
            REFRESH_COOKIE_NAME,
            refresh,
            httponly=True,
            secure=secure,
            samesite=samesite,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )


def clear_auth_cookies(response):
    secure, samesite = _cookie_flags()
    response.delete_cookie(ACCESS_COOKIE_NAME, samesite=samesite)
    response.delete_cookie(REFRESH_COOKIE_NAME, samesite=samesite)
