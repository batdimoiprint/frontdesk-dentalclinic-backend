from rest_framework import permissions

class IsRole(permissions.BasePermission):
    """
    Use as: permission_classes = [IsRole('Receptionist')]
    """

    def __init__(self, *allowed_roles):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        user_roles = getattr(user, 'roles', [])
        for r in user_roles:
            if r.lower() in self.allowed_roles:
                return True
        return False
