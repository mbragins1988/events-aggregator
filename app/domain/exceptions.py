# app/domain/exceptions.py
class DomainError(Exception):
    """Базовое исключение домена"""
    pass


class EventNotFoundError(DomainError):
    """Событие не найдено"""
    pass


class EventNotPublishedError(DomainError):
    """Событие не опубликовано"""
    pass
