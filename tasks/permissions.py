from rest_framework.permissions import BasePermission


class IsRepresentative(BasePermission):
    message = "You must be a representative to access this resource."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "representative")
        )


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "customer")
        )