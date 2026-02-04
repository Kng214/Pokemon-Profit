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
    
]