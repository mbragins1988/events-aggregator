class DomainError(Exception):
    """Базовое исключение домена"""


class EventNotFoundError(DomainError):
    """Событие не найдено"""


class EventNotPublishedError(DomainError):
    """Событие не опубликовано"""


class RegistrationDeadlinePassedError(DomainError):
    """Дедлайн регистрации прошел"""


class SeatNotAvailableError(DomainError):
    """Место недоступно"""


class TicketCreationError(DomainError):
    """Ошибка создания билета"""


class TicketNotFoundError(DomainError):
    """Билет не найден"""


class EventAlreadyPassedError(DomainError):
    """Событие уже прошло"""


class IdempotencyConflictError(DomainError):
    """Конфликт идемпотентности — ключ уже использован с другими данными"""
