"""Validated institutional JWT sessions; keeps the legacy issuer compatible."""
from uuid import UUID
import jwt
from backend.application.services.pmv1_services import AuthService
from backend.domain.exceptions.pmv1_exceptions import CredencialesInvalidasError


class ValidatedAuthService(AuthService):
    def decode(self, token: str) -> dict:
        try:
            claims = jwt.decode(
                token, self.jwt_secret, algorithms=["HS256"],
                issuer=self.issuer, audience=self.audience,
                options={"require": ["exp", "iat", "sub", "roles", "iss", "aud"]},
            )
            UUID(claims["sub"])
            if not isinstance(claims["roles"], list) or not all(isinstance(role, str) for role in claims["roles"]):
                raise ValueError("Invalid roles")
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as exc:
            raise CredencialesInvalidasError("Token invalido o expirado") from exc
