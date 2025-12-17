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