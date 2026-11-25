from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Equipment(models.Model):
    name = models.CharField("Название", max_length=120)
    inventory_number = models.CharField("Инвентарный номер", max_length=30, unique=True)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        ordering = ["inventory_number"]
        verbose_name = "устройство"
        verbose_name_plural = "оборудование"

    def __str__(self):
        return f"{self.name} ({self.inventory_number})"


class Reservation(models.Model):
    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, related_name="reservations",
        verbose_name="Оборудование",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Владелец",
    )
    start = models.DateTimeField("Начало")
    end = models.DateTimeField("Окончание")
    purpose = models.CharField("Цель", max_length=240)
    confirmed = models.BooleanField("Подтверждена", default=True)

    class Meta:
        ordering = ["start", "pk"]
        verbose_name = "бронирование"
        verbose_name_plural = "бронирования"

    def __str__(self):
        return f"{self.equipment} — {self.purpose}"

    def clean(self):
        super().clean()
        if self.start and self.end and self.start >= self.end:
            raise ValidationError({"end": "Окончание должно быть позже начала."})
        if not self.confirmed or not self.equipment_id:
            return
        if not Equipment.objects.filter(pk=self.equipment_id, is_active=True).exists():
            raise ValidationError("Нельзя бронировать неактивное оборудование.")
        if self.start and self.end:
            conflicts = Reservation.objects.filter(
                equipment_id=self.equipment_id, confirmed=True,
                start__lt=self.end, end__gt=self.start,
            ).exclude(pk=self.pk)
            if conflicts.exists():
                raise ValidationError(
                    "Оборудование уже забронировано на этот период. Выберите другое время."
                )