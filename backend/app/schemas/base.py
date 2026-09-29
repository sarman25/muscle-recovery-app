from datetime import datetime, timezone
from pydantic import BaseModel, model_validator


class UTCModel(BaseModel):
    """
    Базовый класс для всех схем-ответов API.
    Автоматически помечает все даты как UTC перед отправкой во фронтенд,
    чтобы браузер корректно переводил их в местное время пользователя.
    """

    @model_validator(mode="after")
    def _mark_datetimes_as_utc(self):
        for field_name in self.__class__.model_fields:
            value = getattr(self, field_name, None)
            if isinstance(value, datetime) and value.tzinfo is None:
                setattr(self, field_name, value.replace(tzinfo=timezone.utc))
        return self