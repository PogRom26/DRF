from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Разрешение только для владельца объекта."""

    def has_object_permission(self, request, view, obj):
        # Проверяем, есть ли у объекта поле owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # Если нет поля owner, проверяем, является ли объект пользователем
        return obj == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Разрешение на чтение для всех, изменение только для владельца."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Проверяем, есть ли у объекта поле owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # Если нет поля owner, проверяем, является ли объект пользователем
        return obj == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """Разрешение на чтение для всех, изменение только для админов."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsModerator(permissions.BasePermission):
    """Разрешение для модераторов."""

    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='moderators').exists()

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.groups.filter(name='moderators').exists()


class IsNotModerator(permissions.BasePermission):
    """Разрешение для пользователей, которые НЕ являются модераторами."""

    def has_permission(self, request, view):
        return request.user and not request.user.groups.filter(name='moderators').exists()

    def has_object_permission(self, request, view, obj):
        return request.user and not request.user.groups.filter(name='moderators').exists()


class IsAdminOrModeratorOrReadOnly(permissions.BasePermission):
    """Разрешение: админы и модераторы могут редактировать, все могут читать."""

    def has_permission(self, request, view):
        # Разрешаем безопасные методы (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Для остальных методов проверяем, является ли пользователь админом или модератором
        return request.user and (
                request.user.is_staff or
                request.user.groups.filter(name='moderators').exists()
        )

    def has_object_permission(self, request, view, obj):
        # Разрешаем безопасные методы (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Для остальных методов проверяем, является ли пользователь админом или модератором
        return request.user and (
                request.user.is_staff or
                request.user.groups.filter(name='moderators').exists()
        )


class IsAdminOrModerator(permissions.BasePermission):
    """Разрешение только для админов и модераторов."""

    def has_permission(self, request, view):
        return request.user and (
                request.user.is_staff or
                request.user.groups.filter(name='moderators').exists()
        )

    def has_object_permission(self, request, view, obj):
        return request.user and (
                request.user.is_staff or
                request.user.groups.filter(name='moderators').exists()
        )


class IsModeratorOrReadOnly(permissions.BasePermission):
    """Модераторы могут редактировать, все могут читать."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.groups.filter(name='moderators').exists()

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.groups.filter(name='moderators').exists()


class IsOwnerOrModeratorOrAdmin(permissions.BasePermission):
    """Разрешение для владельца, модератора или админа."""

    def has_object_permission(self, request, view, obj):
        # Проверяем, является ли пользователь владельцем
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True

        # Проверяем, является ли пользователь модератором
        if request.user and request.user.groups.filter(name='moderators').exists():
            return True

        # Проверяем, является ли пользователь админом
        if request.user and request.user.is_staff:
            return True

        return False


class IsCourseOwnerOrModeratorOrAdmin(permissions.BasePermission):
    """Разрешение для владельца курса, модератора или админа."""

    def has_object_permission(self, request, view, obj):
        # Для курсов проверяем владельца
        if hasattr(obj, 'owner'):
            # Проверяем, является ли пользователь владельцем курса
            if obj.owner == request.user:
                return True

        # Проверяем, является ли пользователь модератором
        if request.user and request.user.groups.filter(name='moderators').exists():
            return True

        # Проверяем, является ли пользователь админом
        if request.user and request.user.is_staff:
            return True

        return False


class IsLessonOwnerOrModeratorOrAdmin(permissions.BasePermission):
    """Разрешение для владельца урока, модератора или админа."""

    def has_object_permission(self, request, view, obj):
        # Для уроков проверяем владельца
        if hasattr(obj, 'owner'):
            # Проверяем, является ли пользователь владельцем урока
            if obj.owner == request.user:
                return True

            # Также проверяем, является ли пользователь владельцем курса, к которому относится урок
            if hasattr(obj, 'course') and obj.course.owner == request.user:
                return True

        # Проверяем, является ли пользователь модератором
        if request.user and request.user.groups.filter(name='moderators').exists():
            return True

        # Проверяем, является ли пользователь админом
        if request.user and request.user.is_staff:
            return True

        return False