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


class RegistrationDeadlinePassedError(DomainError):
    """Дедлайн регистрации прошел"""
    pass


class SeatNotAvailableError(DomainError):
    """Место недоступно"""
    pass


class TicketCreationError(DomainError):
    """Ошибка создания билета"""
    pass


class TicketNotFoundError(DomainError):
    """Билет не найден"""
    pass


class EventAlreadyPassedError(DomainError):
    """Событие уже прошло"""
    pass
