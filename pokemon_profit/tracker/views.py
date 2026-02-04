from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import Card, SealedProduct, Purchase, Sale

@login_required
def dashboard(request):
    user = request.user

    cards_qs = Card.objects.filter(user=user)
    sealed_qs = SealedProduct.objects.filter(user=user)

    cards_count = cards_qs.count()
    sealed_count = sealed_qs.count()
    purchases_count = Purchase.objects.filter(user=user).count()
    sales_count = Sale.objects.filter(user=user).count()

    total_sales = (
        Sale.objects.filter(user=user)
        .aggregate(total=Sum("price"))["total"]
        or Decimal("0")
    )

    total_spent_cards = sum((c.total_spent for c in cards_qs), Decimal("0"))
    total_spent_sealed = sum((s.total_spent for s in sealed_qs), Decimal("0"))
    total_spent = total_spent_cards + total_spent_sealed

    realized_profit = total_sales - total_spent

    return render(request, "tracker/dashboard.html", {
        "cards_count": cards_count,
        "sealed_count": sealed_count,
        "purchases_count": purchases_count,
        "sales_count": sales_count,
        "total_sales": total_sales,
        "total_spent": total_spent,
        "realized_profit": realized_profit,
    })

@login_required
def card_list(request):
    cards = Card.objects.filter(user=request.user).select_related("catalog_item").all()
    return render(request, "tracker/card_list.html", {"cards" : cards})

@login_required
def sealed_list(request):
    sealed = SealedProduct.objects.filter(user=request.user).select_related("catalog_item").all()
    return render(request, "tracker/sealed_list.html", {"sealed" : sealed})

@login_required
def purchase_list(request):
    purchases = Purchase.objects.filter(user=request.user).select_related("card", "sealed_product").order_by("-date")
    return render(request, "tracker/purchase_list.html", {"purchases" : purchases})

@login_required
def sale_list(request):
    sales = (
Sale.objects.filter(user=request.user).select_related("card", "sealed_product").order_by("-date"))
    return render(request, "tracker/sale_list.html", {"sales": sales})
def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "tracker/signup.html", {"form": form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "tracker/login.html", {"form": form})

def user_logout(request):
    logout(request)
    return redirect("login")
        




