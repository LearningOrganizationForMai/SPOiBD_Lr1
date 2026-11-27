from django import forms

from .models import Equipment, Reservation


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ("equipment", "start", "end", "purpose")
        widgets = {
            "start": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "end": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "purpose": forms.TextInput(attrs={"placeholder": "Например, защита лабораторной"}),
        }


class CancelForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ()


class FilterForm(forms.Form):
    equipment = forms.ModelChoiceField(
        label="Оборудование", queryset=Equipment.objects.all(), required=False,
        empty_label="Все устройства",
    )
    day = forms.DateField(
        label="Дата начала", required=False, widget=forms.DateInput(attrs={"type": "date"}),
    )