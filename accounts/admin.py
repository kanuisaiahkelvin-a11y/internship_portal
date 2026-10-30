from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CoordinatorRequest, EmployerProfile, StudentProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('-date_joined',)
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'course', 'year_level')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'school', 'course')


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'job_title')
    search_fields = ('user__email', 'company__name')


@admin.register(CoordinatorRequest)
class CoordinatorRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'institution', 'email', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('full_name', 'institution', 'email')
    readonly_fields = ('invite_token', 'user', 'reviewed_by', 'reviewed_at', 'created_at')
