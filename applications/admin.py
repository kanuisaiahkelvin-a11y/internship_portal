from django.contrib import admin

from .models import Application, ApplicationNote, ApplicationStatusHistory, Interview, Offer


class StatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'changed_by', 'note', 'created_at')


class NoteInline(admin.TabularInline):
    model = ApplicationNote
    extra = 0


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0


class OfferInline(admin.StackedInline):
    model = Offer
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'posting', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'posting__company')
    search_fields = (
        'student__email',
        'student__first_name',
        'student__last_name',
        'posting__title',
        'posting__company__name',
    )
    inlines = [StatusHistoryInline, NoteInline, InterviewInline, OfferInline]
