from django.urls import path

from . import views

urlpatterns = [
    path("", views.reservation_list, name="reservation_list"),
    path("equipment/", views.catalog, name="catalog"),
    path("new/", views.reservation_form, name="reservation_create"),
    path("<int:pk>/edit/", views.reservation_form, name="reservation_edit"),
    path("<int:pk>/cancel/", views.reservation_cancel, name="reservation_cancel"),
    path("<int:pk>/delete/", views.reservation_delete, name="reservation_delete"),
]