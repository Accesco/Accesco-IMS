from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

class IMSException(Exception):
    """Base exception for all Accesco Living IMS errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFoundException(IMSException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class UnauthorizedException(IMSException):
    """Exception raised when authentication fails or is missing."""
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(IMSException):
    """Exception raised when access is denied for a user role."""
    def __init__(self, message: str = "Forbidden: Insufficient privileges"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class InsufficientStockException(IMSException):
    """Exception raised when there is not enough inventory to reserve or deduct."""
    def __init__(self, message: str = "Insufficient stock available"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class UserAlreadyExistsException(IMSException):
    """Exception raised when a username or email is already taken."""
    def __init__(self, message: str = "User already exists"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class InvalidCredentialsException(IMSException):
    """Exception raised when login credentials are invalid."""
    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class PaymentVerificationFailedException(IMSException):
    """Exception raised when Razorpay payment signature verification fails."""
    def __init__(self, message: str = "Payment verification failed"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers for FastAPI app."""
    @app.exception_handler(IMSException)
    async def ims_exception_handler(request: Request, exc: IMSException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        with open(r"c:\Users\jxtro\Desktop\WORK\Accesco-IMS\error.log", "w") as f:
            traceback.print_exc(file=f)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )
