from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('students/', views.StudentRecordsView.as_view(), name='student_records'),
    path(
        'students/<int:pk>/',
        views.StudentRecordDetailView.as_view(),
        name='student_record_detail',
    ),
]
