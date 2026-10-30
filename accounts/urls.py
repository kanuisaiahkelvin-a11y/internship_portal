from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.PortalLoginView.as_view(), name='login'),
    path('logout/', views.PortalLogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<int:pk>/', views.profile_detail, name='profile_detail'),

    # Coordinator access requests (universities and internship offices).
    path(
        'coordinator/request/',
        views.coordinator_request,
        name='coordinator_request',
    ),
    path(
        'coordinator/invite/<uuid:token>/',
        views.coordinator_invite,
        name='coordinator_invite',
    ),
    path(
        'coordinator/requests/<int:pk>/approve/',
        views.coordinator_request_approve,
        name='coordinator_request_approve',
    ),
    path(
        'coordinator/requests/<int:pk>/reject/',
        views.coordinator_request_reject,
        name='coordinator_request_reject',
    ),
]
