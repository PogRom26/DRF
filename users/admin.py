from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_course_or_lesson', 'amount', 'payment_method', 'payment_date')
    list_filter = ('payment_method', 'payment_date', 'course', 'lesson')
    search_fields = ('user__email', 'course__title', 'lesson__title')
    list_select_related = ('user', 'course', 'lesson')

    def get_course_or_lesson(self, obj):
        if obj.course:
            return f"Курс: {obj.course.title}"
        elif obj.lesson:
            return f"Урок: {obj.lesson.title}"
        return "-"

    get_course_or_lesson.short_description = 'Оплачено'


class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone', 'city', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone', 'city', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'phone', 'city'),
        }),
    )

    # Дополнительное задание: показываем платежи пользователя в админке
    readonly_fields = ('payments_display',)

    def payments_display(self, obj):
        payments = obj.payments.all()[:5]  # Показываем только последние 5 платежей
        if payments:
            return "<br>".join([f"{p.payment_date.date()}: {p.amount} руб. ({p.get_payment_method_display()})"
                                for p in payments])
        return "Нет платежей"

    payments_display.short_description = 'Последние платежи'
    payments_display.allow_tags = True


admin.site.register(User, CustomUserAdmin)