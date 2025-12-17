from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Разрешение только для владельца объекта."""

    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Разрешение на чтение для всех, изменение только для владельца."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
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