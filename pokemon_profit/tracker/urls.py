from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cards/", views.card_list, name="card_list"),
    path("sealed/", views.sealed_list, name="sealed_list"),
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("sales/", views.sale_list, name="sale_list"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("cards/add/", views.card_create, name="card_create"),
    path("sealed/add/", views.sealed_create, name="sealed_create"),
    path("purchases/add/", views.purchase_create, name="purchase_create"),
    path("sales/add/", views.sale_create, name="sale_create"),
    path("cards/<int:pk>/edit/", views.card_edit, name="card_edit"),
    path("cards/<int:pk>/delete/", views.card_delete, name="card_delete"),
    path("sealed/<int:pk>/edit/", views.sealed_edit, name="sealed_edit"),
    path("sealed/<int:pk>/delete/", views.sealed_delete, name="sealed_delete"),
    path("purchases/<int:pk>/edit/", views.purchase_edit, name="purchase_edit"),
    path("purchases/<int:pk>/delete/", views.purchase_delete, name="purchase_delete"),
    path("sales/<int:pk>/edit/", views.sale_edit, name="sale_edit"),
    path("sales/<int:pk>/delete/", views.sale_delete, name="sale_delete"),
]