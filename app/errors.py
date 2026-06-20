"""Application-level exceptions."""

from __future__ import annotations


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 400,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str, *, details: object | None = None) -> None:
        super().__init__(message, code="not_found", status_code=404, details=details)


class ValidationAppError(AppError):
    def __init__(self, message: str, *, details: object | None = None) -> None:
        super().__init__(
            message,
            code="validation_error",
            status_code=422,
            details=details,
        )


class ConnectionFailedError(AppError):
    def __init__(self, message: str, *, details: object | None = None) -> None:
        super().__init__(
            message,
            code="connection_failed",
            status_code=400,
            details=details,
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required.", *, details: object | None = None) -> None:
        super().__init__(message, code="unauthorized", status_code=401, details=details)


class UnknownConnectorError(AppError):
    def __init__(self, connector_type: str) -> None:
        super().__init__(
            f"Unknown connector type: {connector_type}",
            code="unknown_connector",
            status_code=400,
            details={"connector_type": connector_type},
        )
