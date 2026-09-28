from rest_framework.permissions import BasePermission

from .models import User


class HasRole(BasePermission):
    roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in self.roles
        )


class IsCitoyen(HasRole):
    roles = (User.Role.CITOYEN,)


class IsBenevole(HasRole):
    roles = (User.Role.BENEVOLE,)


class IsVeterinaire(HasRole):
    roles = (User.Role.VETERINAIRE,)


class IsRefuge(HasRole):
    roles = (User.Role.REFUGE,)


class IsAdmin(HasRole):
    roles = (User.Role.ADMIN,)


class IsRefugeOrAdmin(HasRole):
    roles = (User.Role.REFUGE, User.Role.ADMIN)
