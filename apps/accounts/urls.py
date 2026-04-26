# accounts/urls.py - URL routing ของ accounts
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',          views.login_view,         name='login'),
    path('register/',       views.register_view,      name='register'),
    path('logout/',         views.logout_view,         name='logout'),
    path('password-reset/',                                  views.password_reset_view,         name='password_reset'),
    path('password-reset/done/',                             views.password_reset_done_view,     name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/',         views.password_reset_confirm_view,  name='password_reset_confirm'),
    path('password-reset/complete/',                         views.password_reset_complete_view, name='password_reset_complete'),
    path('profile/',          views.profile_view,          name='profile'),
    path('register/pending/',    views.register_pending_view, name='register_pending'),
    path('verify-email/',        views.verify_email_view,     name='verify_email'),
    path('verify-email/cancel/', views.cancel_verify_view,    name='verify_email_cancel'),
]
