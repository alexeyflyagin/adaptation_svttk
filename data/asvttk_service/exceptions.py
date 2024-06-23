
class AccessError(Exception):
    pass


class TrainingIsActiveError(Exception):
    pass


class TrainingHasStudentsError(Exception):
    pass


class TrainingIsNotActiveError(Exception):
    pass


class TrainingAlreadyHasThisStateError(Exception):
    pass


class UnknownError(Exception):
    pass


class TrainingIsEmptyError(Exception):
    pass


class TrainingNotFoundError(Exception):
    pass


class InitialsValueError(Exception):
    pass


class EmptyFieldError(Exception):
    pass


class KeyIsBusyError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class KeyHasSessionError(Exception):
    pass


class KeyNotFoundError(Exception):
    pass


class ObjectNotFoundError(Exception):
    def __init__(self, object_type: str):
        super().__init__(f"This object ({object_type}) was not found")


class TokenNotValidError(Exception):
    pass


class RoleNotUniqueNameError(Exception):
    pass


class NotFoundError(Exception):
    pass


class LevelAnswerAlreadyExistsError(Exception):
    pass


class NoArgsError(Exception):
    pass
