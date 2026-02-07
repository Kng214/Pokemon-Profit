from django import forms
from .models import Card, SealedProduct, Purchase, Sale, CatalogItem

class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ["name", "set_name", "card_number", "printing", "condition", "catalog", "catalog_id_str", "catalog_item"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show card items (not sealed)
        self.fields["catalog_item"].queryset = CatalogItem.objects.filter(is_sealed=False).order_by("name")

class SealedProductForm(forms.ModelForm):
    class Meta:
        model = SealedProduct
        fields = ["name", "set_name", "quantity", "catalog_item"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["catalog_item"].queryset = CatalogItem.objects.filter(is_sealed=True).order_by("name")

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ["date", "card", "sealed_product", "quantity", "price_each"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        card = cleaned.get("card")
        sealed = cleaned.get("sealed_product")
        if (card is None and sealed is None) or (card is not None and sealed is not None):
            raise forms.ValidationError("Select either a Card or a Sealed Product (not both).")
        return cleaned

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["date", "card", "sealed_product", "price", "platform"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
    
    def clean(self):
        cleaned = super().clean()
        card = cleaned.get("card")
        sealed = cleaned.get("sealed_product")
        if (card is None and sealed is None) or (card is not None and sealed is not None):
            raise forms.ValidationError("Select either a Card or a Sealed Product (not both).")
        return cleaned

