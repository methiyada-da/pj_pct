# admin_panel/middleware.py - middleware ตรวจสอบการตั้งค่าระบบเบื้องต้น
from django.shortcuts import redirect
from django.urls import reverse


class AdminSetupMiddleware:
    """
    ตรวจสอบทุก request ว่าระบบมี admin ผูกอยู่หรือยัง
    ถ้ายังไม่มี → เด้งไปหน้า setup ก่อนเสมอ
    ถ้ามีแล้ว → ปล่อยผ่านตามปกติ
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # import ใน __call__ เพื่อหลีกเลี่ยง app registry ยังไม่พร้อม
        from .models import System

        setup_url = reverse('admin_panel:admin_setup')

        # URL ที่อนุญาตให้เข้าได้โดยไม่ต้องมี admin (whitelist)
        allowed_prefixes = [
            setup_url,
            '/static/',
            '/media/',
            '/admin/',       # Django admin สำหรับ superuser
            '/favicon.ico',
            '/accounts/',
            '/notifications/',
            '/messaging/',
        ]

        # ถ้า path ปัจจุบันอยู่ใน whitelist → ปล่อยผ่าน
        if any(request.path.startswith(p) for p in allowed_prefixes):
            return self.get_response(request)

        # ตรวจว่ามี admin ในระบบหรือยัง
        system = System.objects.select_related('admin').first()
        has_admin = system and system.admin is not None

        if not has_admin:
            # ยังไม่มี admin → เด้งไปหน้า setup เสมอ
            return redirect(setup_url)

        return self.get_response(request)
