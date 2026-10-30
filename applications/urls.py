from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import path

from . import views

app_name = 'applications'


@login_required
def application_index(request):
    if request.user.is_student:
        return redirect('applications:my_applications')
    if request.user.is_employer or request.user.is_coordinator:
        return redirect('applications:review_list')
    messages.info(request, 'Your account has no application workspace.')
    return redirect('dashboard:home')


urlpatterns = [
    path('', application_index, name='index'),
    path('mine/', views.MyApplicationsView.as_view(), name='my_applications'),
    path('review/', views.ReviewApplicationsView.as_view(), name='review_list'),
    path('apply/<int:pk>/', views.ApplyView.as_view(), name='apply'),

    path('<int:pk>/', views.ApplicationDetailView.as_view(), name='detail'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
    path('<int:pk>/note/', views.add_note, name='add_note'),
    path('<int:pk>/interview/', views.ScheduleInterviewView.as_view(), name='schedule_interview'),
    path('<int:pk>/offer/', views.ExtendOfferView.as_view(), name='extend_offer'),
    path('<int:pk>/respond/', views.respond_offer, name='respond_offer'),
    path('<int:pk>/withdraw/', views.withdraw_application, name='withdraw'),
]
