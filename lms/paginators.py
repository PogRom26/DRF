from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class LessonPaginator(PageNumberPagination):
    """Пагинатор для уроков."""

    page_size = 10  # Количество элементов на странице по умолчанию
    page_size_query_param = 'page_size'  # Параметр для изменения количества элементов на странице
    max_page_size = 50  # Максимальное количество элементов на странице

    def get_paginated_response(self, data):
        """Кастомный ответ с пагинацией."""
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class CoursePaginator(PageNumberPagination):
    """Пагинатор для курсов."""

    page_size = 5  # Меньше курсов на странице, так как они более объемные
    page_size_query_param = 'page_size'
    max_page_size = 20

    def get_paginated_response(self, data):
        """Кастомный ответ с пагинацией."""
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class SubscriptionPaginator(PageNumberPagination):
    """Пагинатор для подписок."""

    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 30