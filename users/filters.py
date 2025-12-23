import django_filters
from .models import Payment


class PaymentFilter(django_filters.FilterSet):
    """Фильтры для платежей."""

    # Фильтрация по курсу
    course = django_filters.NumberFilter(field_name='course__id')

    # Фильтрация по уроку
    lesson = django_filters.NumberFilter(field_name='lesson__id')

    # Фильтрация по способу оплаты
    payment_method = django_filters.ChoiceFilter(
        choices=Payment.PAYMENT_METHODS
    )

    # Фильтрация по статусу платежа
    payment_status = django_filters.ChoiceFilter(
        choices=[
            ('pending', 'Ожидает оплаты'),
            ('processing', 'В обработке'),
            ('succeeded', 'Успешно'),
            ('failed', 'Неудачно'),
            ('refunded', 'Возвращено'),
        ]
    )

    # Сортировка
    ordering = django_filters.OrderingFilter(
        fields=(
            ('payment_date', 'payment_date'),
            ('-payment_date', '-payment_date'),
            ('amount', 'amount'),
            ('-amount', '-amount'),
        ),
        field_labels={
            'payment_date': 'Дате оплаты (по возрастанию)',
            '-payment_date': 'Дате оплаты (по убыванию)',
            'amount': 'Сумме (по возрастанию)',
            '-amount': 'Сумме (по убыванию)',
        }
    )

    class Meta:
        model = Payment
        fields = ['course', 'lesson', 'payment_method', 'payment_status']