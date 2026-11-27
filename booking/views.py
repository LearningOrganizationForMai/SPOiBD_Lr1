from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import CancelForm, FilterForm, ReservationForm
from .models import Equipment, Reservation


@login_required
def catalog(request):
    now = timezone.now()
    in_use = Reservation.objects.filter(
        equipment=OuterRef("pk"), confirmed=True, start__lte=now, end__gt=now,
    )
    devices = Equipment.objects.annotate(busy=Exists(in_use))
    return render(request, "booking/catalog.html", {"devices": devices})


@login_required
def reservation_list(request):
    items = Reservation.objects.filter(user=request.user).select_related("equipment")
    filters = FilterForm(request.GET)
    if filters.is_valid():
        equipment = filters.cleaned_data["equipment"]
        if equipment:
            items = items.filter(equipment=equipment)
        day = filters.cleaned_data["day"]
        if day:
            items = items.filter(start__date=day)
    else:
        items = items.none()
    return render(request, "booking/list.html", {"items": items, "filters": filters})


@login_required
@require_http_methods(["GET", "POST"])
def reservation_form(request, pk=None):
    if request.method == "POST":
        with transaction.atomic():
            item = (get_object_or_404(Reservation, pk=pk, user=request.user)
                    if pk is not None else Reservation(user=request.user))
            form = ReservationForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                messages.success(request, "Бронирование сохранено.")
                return redirect("reservation_list")
    else:
        item = get_object_or_404(Reservation, pk=pk, user=request.user) if pk is not None else None
        form = ReservationForm(instance=item, initial={} if item else {"equipment": request.GET.get("equipment")})
    return render(request, "booking/form.html", {"form": form, "editing": pk is not None})


@login_required
@require_POST
@transaction.atomic
def reservation_cancel(request, pk):
    item = get_object_or_404(Reservation, pk=pk, user=request.user)
    item.confirmed = False
    form = CancelForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, "Бронь отменена. Запись сохранена в истории.")
    else:
        messages.error(request, "Не удалось отменить бронь. Проверьте данные записи.")
    return redirect("reservation_list")


@login_required
@require_POST
@transaction.atomic
def reservation_delete(request, pk):
    item = get_object_or_404(Reservation, pk=pk, user=request.user)
    item.delete()
    messages.success(request, "Бронирование удалено.")
    return redirect("reservation_list")