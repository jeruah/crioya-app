from fastapi import status

class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Error interno"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)

class DatabaseError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
