class DomainError(Exception):
    """Base de los errores de negocio."""


class InvalidLocation(DomainError):
    """La ubicación recibida no es válida (coordenadas fuera de rango, NaN, etc.)."""
