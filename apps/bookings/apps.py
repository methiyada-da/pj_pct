from django.apps import AppConfig


class BookingsConfig(AppConfig):
    name = 'apps.bookings'

    def ready(self):
        import apps.bookings.signals  # โหลดสัญญาณเมื่อแอปพร้อม
