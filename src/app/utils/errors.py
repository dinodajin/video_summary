class AppError(Exception):
    """Base application error shown to users."""


class ValidationError(AppError):
    pass


class MediaError(AppError):
    pass


class SttError(AppError):
    pass


def to_user_message(err: Exception) -> str:
    if isinstance(err, ValidationError):
        return str(err)
    if isinstance(err, MediaError):
        return str(err)
    if isinstance(err, SttError):
        return f"전사 처리 중 오류가 발생했습니다: {err}"
    return f"알 수 없는 오류가 발생했습니다: {err}"
