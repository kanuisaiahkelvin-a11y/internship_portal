from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin):
    """Restrict a view to the given roles. Coordinators can access everything."""

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not self.user_has_access(request.user):
            messages.error(request, 'You do not have permission to access that page.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)

    def user_has_access(self, user):
        return user.is_coordinator or user.role in self.allowed_roles


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('student',)


class EmployerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('employer',)


class CoordinatorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('coordinator',)
