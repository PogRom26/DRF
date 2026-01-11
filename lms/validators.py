import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from rest_framework import serializers


def validate_youtube_url(value):
    """Функция-валидатор для проверки YouTube ссылок."""
    if not value:
        return value

    parsed_url = urlparse(value)

    # Допустимые домены YouTube
    youtube_domains = [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be",
    ]

    # Получаем домен из URL
    domain = parsed_url.netloc.lower()

    # Проверяем, соответствует ли домен youtube
    for youtube_domain in youtube_domains:
        if domain == youtube_domain or domain.endswith("." + youtube_domain):
            return value

    # Проверяем пути для youtu.be
    if domain in ["youtu.be", "www.youtu.be"]:
        return value

    raise ValidationError("Ссылка должна вести на youtube.com")


class YouTubeURLValidator:
    """Валидатор для проверки, что ссылка ведет на youtube.com."""

    def __init__(self, field="video_url"):
        self.field = field

    def __call__(self, attrs):
        """Проверяем URL на принадлежность к YouTube."""
        url = attrs.get(self.field)

        if url:
            try:
                validate_youtube_url(url)
            except ValidationError as e:
                raise serializers.ValidationError({self.field: str(e)})

        return attrs


class NoExternalLinksValidator:
    """Валидатор для проверки отсутствия внешних ссылок в тексте."""

    def __init__(self, fields=["description"]):
        self.fields = fields if isinstance(fields, list) else [fields]

    def __call__(self, attrs):
        """Проверяет наличие внешних ссылок в указанных полях."""
        for field in self.fields:
            text = attrs.get(field, "")

            if text:
                # Ищем URL в тексте
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)

                for url in urls:
                    # Парсим найденный URL
                    if not url.startswith(("http://", "https://")):
                        url = "http://" + url

                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()

                    # Проверяем, является ли это НЕ youtube ссылкой
                    if not any(
                        youtube_domain in domain
                        for youtube_domain in ["youtube.com", "youtu.be"]
                    ):
                        raise serializers.ValidationError(
                            {
                                field: f"Обнаружена внешняя ссылка: {url}. "
                                "Разрешены только ссылки на youtube.com"
                            }
                        )

        return attrs
