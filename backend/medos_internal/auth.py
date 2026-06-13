"""Custom authentication backends with token expiry support.

DRF's default ``TokenAuthentication`` never expires tokens. This module
provides an ``ExpiringTokenAuthentication`` that rejects tokens older than
``settings.TOKEN_EXPIRY_DAYS`` (default 7).
"""
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


TOKEN_EXPIRY_DAYS = getattr(settings, 'TOKEN_EXPIRY_DAYS', 7)


def token_is_expired(token) -> bool:
    """Return True if the token is older than TOKEN_EXPIRY_DAYS."""
    if token.created is None:
        return True
    age = timezone.now() - token.created
    return age.days >= TOKEN_EXPIRY_DAYS


def regenerate_token(token):
    """Delete the old token and return a new one for the same user."""
    user = token.user
    token.delete()
    from rest_framework.authtoken.models import Token
    return Token.objects.create(user=user)


class ExpiringTokenAuthentication(TokenAuthentication):
    """Like DRF's TokenAuthentication, but rejects expired tokens."""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token_is_expired(token):
            raise AuthenticationFailed('Token has expired. Please log in again.')
        return user, token
