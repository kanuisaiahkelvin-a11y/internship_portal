from django.urls import path

from . import views

app_name = 'opportunities'

urlpatterns = [
    path('', views.PostingListView.as_view(), name='posting_list'),
    path('new/', views.PostingCreateView.as_view(), name='posting_create'),
    path('mine/', views.MyPostingsView.as_view(), name='my_postings'),
    path('review/', views.ReviewPostingsView.as_view(), name='review_postings'),
    path('saved/', views.BookmarkListView.as_view(), name='bookmark_list'),

    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/new/', views.CompanyCreateView.as_view(), name='company_create'),
    path('companies/<int:pk>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('companies/<int:pk>/edit/', views.CompanyUpdateView.as_view(), name='company_edit'),
    path('companies/<int:pk>/verify/', views.verify_company, name='company_verify'),

    path('<int:pk>/', views.PostingDetailView.as_view(), name='posting_detail'),
    path('<int:pk>/edit/', views.PostingUpdateView.as_view(), name='posting_edit'),
    path('<int:pk>/delete/', views.PostingDeleteView.as_view(), name='posting_delete'),
    path('<int:pk>/submit/', views.submit_posting, name='posting_submit'),
    path('<int:pk>/close/', views.close_posting, name='posting_close'),
    path('<int:pk>/approve/', views.approve_posting, name='posting_approve'),
    path('<int:pk>/reject/', views.reject_posting, name='posting_reject'),
    path('<int:pk>/bookmark/', views.bookmark_toggle, name='bookmark_toggle'),
]
