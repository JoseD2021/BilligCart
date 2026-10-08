class DomainError(Exception):
    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class EmailAlreadyRegistered(DomainError):
    pass

class InvalidEmail(DomainError):
    pass

class WeakPassword(DomainError):
    pass

class InvalidCredentials(DomainError):
    pass

class UserNotFound(DomainError):
    pass

class InvalidRequestBodyError(DomainError):
    pass