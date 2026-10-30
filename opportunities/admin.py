from django.contrib import admin

from .models import Bookmark, Company, InternshipPosting


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'location', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'industry')
    search_fields = ('name', 'location', 'industry', 'contact_email')


@admin.register(InternshipPosting)
class InternshipPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'status', 'work_mode', 'slots', 'application_deadline')
    list_filter = ('status', 'work_mode', 'is_featured', 'company')
    search_fields = ('title', 'company__name', 'skills_required')
    date_hierarchy = 'created_at'


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'posting', 'created_at')
    search_fields = ('user__email', 'posting__title')
