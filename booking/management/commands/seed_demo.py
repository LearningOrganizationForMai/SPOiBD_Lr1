from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from booking.models import Equipment


class Command(BaseCommand):
    help = "Добавляет три учебных устройства и два обычных аккаунта для локальной ЛР."

    @transaction.atomic
    def handle(self, *args, **options):
        devices = [
            ("LAB-001", "Проектор Epson", True),
            ("LAB-002", "Ноутбук Lenovo", True),
            ("LAB-003", "Документ-камера", False),
        ]
        for number, name, active in devices:
            Equipment.objects.get_or_create(
                inventory_number=number, defaults={"name": name, "is_active": active},
            )
        User = get_user_model()
        for username in ("roman", "arina"):
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, password="SPOiBD-26!")
        self.stdout.write(self.style.SUCCESS("Учебные данные готовы."))