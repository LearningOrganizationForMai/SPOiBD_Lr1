from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Equipment, Reservation


class BookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("first")
        cls.other = User.objects.create_user("second")
        cls.projector = Equipment.objects.create(name="Проектор", inventory_number="P1")
        cls.laptop = Equipment.objects.create(name="Ноутбук", inventory_number="L2")

    def setUp(self):
        self.client.force_login(self.owner)
        self.data = {
            "equipment": self.projector.pk, "start": "2027-03-15T10:00",
            "end": "2027-03-15T11:00", "purpose": "Защита",
        }

    def create(self, **changes):
        return self.client.post(reverse("reservation_create"), {**self.data, **changes})

    def test_owner_comes_from_session(self):
        self.assertRedirects(self.create(user=self.other.pk), reverse("reservation_list"))
        self.assertEqual(Reservation.objects.get().user, self.owner)

    def test_empty_or_inverted_interval(self):
        for end in ["2027-03-15T10:00", "2027-03-15T09:00"]:
            self.assertContains(self.create(end=end), "Окончание должно быть позже")
        self.assertFalse(Reservation.objects.exists())

    def test_conflict_including_another_owner(self):
        self.create()
        self.client.force_login(self.other)
        for start, end in [("09:30", "10:30"), ("10:30", "11:30"), ("09:00", "12:00"),
                           ("10:15", "10:45"), ("10:00", "11:00")]:
            result = self.create(start="2027-03-15T" + start, end="2027-03-15T" + end)
            self.assertContains(result, "Выберите другое время")
        self.assertEqual(Reservation.objects.count(), 1)

    def test_other_device_and_boundary(self):
        self.create()
        self.create(equipment=self.laptop.pk)
        self.create(start="2027-03-15T11:00", end="2027-03-15T12:00")
        self.assertEqual(Reservation.objects.count(), 3)

    def test_inactive_device(self):
        self.projector.is_active = False
        self.projector.save()
        self.assertContains(self.create(), "неактивное оборудование")
        self.assertFalse(Reservation.objects.exists())

    def test_edit_self_and_reject_conflicting_edit(self):
        self.create()
        first = Reservation.objects.get()
        url = reverse("reservation_edit", args=[first.pk])
        self.client.post(url, {**self.data, "purpose": "Практика"})
        first.refresh_from_db()
        self.assertEqual(first.purpose, "Практика")
        self.create(start="2027-03-15T11:00", end="2027-03-15T12:00")
        self.assertContains(self.client.post(url, {**self.data, "end": "2027-03-15T11:15"}), "Выберите другое время")
        first.refresh_from_db()
        self.assertEqual(timezone.localtime(first.end).hour, 11)

    def test_foreign_record(self):
        self.create()
        pk = Reservation.objects.get().pk
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("reservation_list")), "Защита")
        self.assertEqual(self.client.get(reverse("reservation_edit", args=[pk])).status_code, 404)
        for action in ["edit", "cancel", "delete"]:
            url = reverse("reservation_" + action, args=[pk])
            self.assertEqual(self.client.post(url, {**self.data, "purpose": "Изменение"}).status_code, 404)
        item = Reservation.objects.get(pk=pk)
        self.assertEqual(item.purpose, "Защита")
        self.assertTrue(item.confirmed)

    def test_cancel_rebook_and_delete(self):
        self.create()
        pk = Reservation.objects.get().pk
        self.client.post(reverse("reservation_cancel", args=[pk]))
        self.assertFalse(Reservation.objects.get(pk=pk).confirmed)
        self.assertRedirects(self.create(), reverse("reservation_list"))
        self.assertEqual(Reservation.objects.count(), 2)
        self.client.post(reverse("reservation_delete", args=[pk]))
        self.assertFalse(Reservation.objects.filter(pk=pk).exists())
        self.assertEqual(Reservation.objects.count(), 1)

    def test_methods_and_csrf(self):
        self.create()
        pk = Reservation.objects.get().pk
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner)
        for action in ["cancel", "delete"]:
            url = reverse("reservation_" + action, args=[pk])
            self.assertEqual(strict.get(url).status_code, 405)
            self.assertEqual(strict.post(url).status_code, 403)
        self.assertTrue(Reservation.objects.get().confirmed)

    def test_filter_and_invalid_date(self):
        self.create()
        self.create(equipment=self.laptop.pk, purpose="Чтение")
        url = reverse("reservation_list")
        filters = {"equipment": self.laptop.pk, "day": "2027-03-15"}
        page = self.client.get(url, filters)
        self.assertContains(page, "Чтение")
        self.assertNotContains(page, "Защита")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(url, filters), "Чтение")
        self.assertContains(self.client.get(url, {"day": "xyz"}), "Записей нет")

    def test_catalog_reports_current_availability(self):
        now = timezone.localtime()
        self.create(start=(now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M"),
                    end=(now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M"))
        page = self.client.get(reverse("catalog"))
        self.assertContains(page, "Занято сейчас")
        self.assertContains(page, "Свободно сейчас")

    def test_anonymous_redirect(self):
        self.client.logout()
        response = self.client.get(reverse("reservation_list"))
        self.assertRedirects(response, reverse("login") + "?next=/booking/")