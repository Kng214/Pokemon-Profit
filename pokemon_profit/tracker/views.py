from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import CardForm, SealedProductForm, PurchaseForm, SaleForm
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
        
@login_required
def card_create(request):
    if request.method == "POST":
        form = CardForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            form.save_m2m()
            return redirect("card_list")
    else:
        form = CardForm()
    return render(request, "tracker/form.html", {"form": form, "title": "Add Card"})

@login_required
def sealed_create(request):
    if request.method == "POST":
        form = SealedProductForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect("sealed_list")
    else:
        form = SealedProductForm()
    return render(request, "tracker/form.html", {"form": form, "title": "Add Sealed Product"})

@login_required
def purchase_create(request):
    if request.method == "POST":
        form = PurchaseForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            if obj.card and obj.card.user_id != request.user.id:
                form.add_error("card", "That card is not yours.")
            elif obj.sealed_product and obj.sealed_product.user_id != request.user.id:
                form.add_error("sealed_product", "That sealed product is not yours.")
            else:
                obj.save()
                return redirect("purchase_list")
    else:
        form = PurchaseForm()
        form.fields["card"].queryset = form.fields["card"].queryset.filter(user=request.user)
        form.fields["sealed_product"].queryset = form.fields["sealed_product"].queryset.filter(user=request.user)
    return render(request, "tracker/form.html", {"form": form, "title": "Add Purchase"})

@login_required
def sale_create(request):
    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            
            if obj.card and obj.card.user_id != request.user.id:
                form.add_error("card", "That card is not yours.")
            elif obj.sealed_product and obj.sealed_product.user_id != request.user.id:
                form.add_error("sealed_product", "That sealed product is not yours.")
            else:
                obj.save()
                return redirect("sale_list")
    else:
        form = SaleForm()
        form.fields["card"].queryset = form.fields["card"].queryset.filter(user=request.user)
        form.fields["sealed_product"].queryset = form.fields["sealed_product"].queryset.filter(user=request.user)
    return render(request, "tracker/form.html", {"form": form, "title": "Add Sale"})

@login_required
def card_edit(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)
    if request.method == "POST":
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            form.save_m2m()
            return redirect("card_list")
    else:
        form = CardForm(instance=card)
    return render(request, "tracker/form.html", {"form": form, "title": "Edit Card"})

@login_required
def card_delete(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)
    if request.method == "POST":
        card.delete()
        return redirect("card_list")
    return render(request, "tracker/confirm_delete.html", {
        "title": "Delete Card",
        "object": card,
        "cancel_url": "card_list",
    })

@login_required
def sealed_edit(request, pk):
    sealed = get_object_or_404(SealedProduct, pk=pk, user=request.user)
    if request.method == "POST":
        form = SealedProductForm(request.POST, instance=sealed)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect("sealed_list")
    else:
        form = SealedProductForm(instance=sealed)
    return render(request, "tracker/form.html", {"form": form, "title": "Edit Sealed Product"})

@login_required
def sealed_delete(request, pk):
    sealed = get_object_or_404(SealedProduct, pk=pk, user=request.user)
    if request.method == "POST":
        sealed.delete()
        return redirect("sealed_list")
    return render(request, "tracker/confirm_delete.html", {
        "title": "Delete Sealed Product",
        "object": sealed,
        "cancel_url": "sealed_list",
    })

@login_required
def purchase_edit(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk, user=request.user)
    if request.method == "POST":
        form = PurchaseForm(request.POST, instance=purchase)
        form.fields["card"].queryset = Card.objects.filter(user=request.user)
        form.fields["sealed_product"].queryset = SealedProduct.objects.filter(user=request.user)
        
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect("purchase_list")
    else:
        form = PurchaseForm(instance=purchase)
        form.fields["card"].queryset = Card.objects.filter(user=request.user)
        form.fields["sealed_product"].queryset = SealedProduct.objects.filter(user=request.user)
    return render(request, "tracker/form.html", {"form": form, "title": "Edit Purchase"})

@login_required
def purchase_delete(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk, user=request.user)
    if request.method == "POST":
        purchase.delete()
        return redirect("purchase_list")
    return render(request, "tracker/confirm_delete.html", {
        "title": "Delete Purchase",
        "object": purchase,
        "cancel_url": "purchase_list",
    })

@login_required
def sale_edit(request, pk):
    sale = get_object_or_404(Sale, pk=pk, user=request.user)
    if request.method == "POST":
        form = SaleForm(request.POST, instance=sale)
        form.fields["card"].queryset = Card.objects.filter(user=request.user)
        form.fields["sealed_product"].queryset = SealedProduct.objects.filter(user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect("sale_list")
    else:
        form = SaleForm(instance=sale)
        form.fields["card"].queryset = Card.objects.filter(user=request.user)
        form.fields["sealed_product"].queryset = SealedProduct.objects.filter(user=request.user)
    return render(request, "tracker/form.html", {"form": form, "title": "Edit Sale"})

@login_required
def sale_delete(request, pk):
    sale = get_object_or_404(Sale, pk=pk, user=request.user)
    if request.method == "POST":
        sale.delete()
        return redirect("sale_list")
    return render(request, "tracker/confirm_delete.html", {
        "title": "Delete Sale",
        "object": sale,
        "cancel_url": "sale_list",
    })