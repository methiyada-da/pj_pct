"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# import home view โดยตรง
from apps.accounts.views import home_view


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
 
    # หน้าแรก
    path('', home_view, name='home'),
 
    # Accounts (login, register, logout, …)
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),

    path('panel/',     include('apps.admin_panel.urls', namespace='admin_panel')),
    path('courses/',   include('apps.courses.urls',     namespace='courses')),
    path('tutoring/',  include('apps.tutoring.urls',    namespace='tutoring')),
    path('credits/',   include('apps.credits.urls',     namespace='credits')),
    path('bookings/',  include('apps.bookings.urls',    namespace='bookings')),
    path('messaging/', include('apps.messaging.urls', namespace='messaging')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
]
 
# Serve media files ในโหมด development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
 