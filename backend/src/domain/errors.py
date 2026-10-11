import datetime

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

class NoOffersFound(DomainError):
    def __init__(self, ingredient_name: str):
        super().__init__(f"No offers found for ingredient: {ingredient_name}")
        self.ingredient_name = ingredient_name
        
class IngredienteNotFound(DomainError):
    def __init__(self, ingredient_id: int):
        super().__init__(f"Ingredient with ID {ingredient_id} not found")
        self.ingredient_id = ingredient_id
        
class ScrapingError(DomainError):
    def __init__(self, url: str, original_exception: Exception):
        super().__init__(f"Error scraping URL {url}: {str(original_exception)}")
        self.url = url
        self.original_exception = original_exception
        
class IngredienteRecentlyUpdated(DomainError):
    def __init__(self, ingredient_id: int, last_updated: datetime.datetime):
        super().__init__(f"Ingredient with ID {ingredient_id} was recently updated on {last_updated}")
        self.ingredient_id = ingredient_id
        self.last_updated = last_updated