from django.db import models
from django.forms import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.conf import settings

MONEY_Q = Decimal("0.01")

def money(v) -> Decimal:
    return (v or Decimal("0")).quantize(MONEY_Q, rounding=ROUND_HALF_UP)

class Card(models.Model):
    name = models.CharField(max_length=100)
    set_name = models.CharField(max_length=255, blank=True, default="")
    card_number = models.CharField(max_length=32, blank=True, default="")
    printing = models.CharField(max_length=64, blank=True, default="Normal")
    condition = models.CharField(max_length = 20, blank=True)
    catalog = models.ForeignKey("CardCatalog", null=True, blank=True, on_delete=models.SET_NULL)
    catalog_id_str = models.CharField(max_length=80, blank=True, null=True)
    catalog_item = models.ForeignKey("CatalogItem", null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_cards")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards")
    
    @property
    def current_market_value(self):
        latest_manual = self.marketprice_set.order_by("-date").first()
        if latest_manual and latest_manual.price is not None:
            return money(latest_manual.price)

        if self.catalog_item_id:
            snap = self.catalog_item.prices.order_by("-captured_at").first()
            if snap and snap.market is not None:
                return money(snap.market)

        return Decimal("0.00")

    @property
    def total_spent(self):
        return money(sum((p.total_price for p in self.purchase_set.all()), Decimal("0")))

    @property
    def total_sales(self):
        return money(sum((s.price for s in self.sale_set.all()), Decimal("0")))

    @property
    def realized_profit(self):
        return money(self.total_sales - self.total_spent)

    @property
    def unrealized_profit(self):
        return money(self.current_market_value - self.total_spent)
    
    def __str__(self):
        return f"{self.name} ({self.set_name} {self.card_number})"

    

class SealedProduct(models.Model):
    name = models.CharField(max_length=200)
    set_name = models.CharField(max_length=200, blank=True, default="")
    quantity = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sealed_products")

    catalog_item = models.ForeignKey(
        "CatalogItem",
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    def _spent_expr(self):
        return ExpressionWrapper(
            F("quantity") * F("price_each"),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )

    @property
    def current_market_value(self):
        latest_manual = self.marketprice_set.order_by("-date").first()
        if latest_manual and latest_manual.price is not None:
            return money(latest_manual.price * (self.quantity or 0))

        if self.catalog_item_id:
            snap = self.catalog_item.prices.order_by("-captured_at").first()
            if snap and snap.market is not None:
                return money(snap.market * (self.quantity or 0))

        return Decimal("0.00")

    @property
    def total_spent(self):
        total = self.purchase_set.filter(sealed_product=self).aggregate(
            total=Coalesce(Sum(self._spent_expr()), Decimal("0"))
        )["total"]
        return money(total)

    @property
    def total_sales(self):
        total = self.sale_set.filter(sealed_product=self).aggregate(
            total=Coalesce(Sum("price"), Decimal("0"))
        )["total"]
        return money(total)

    @property
    def realized_profit(self):
        return money(self.total_sales - self.total_spent)
    
    @property
    def unrealized_profit(self):
        return money(self.current_market_value - self.total_spent)
    
class Purchase(models.Model):
    card = models.ForeignKey("Card", null=True, blank=True, on_delete=models.CASCADE)
    sealed_product = models.ForeignKey("SealedProduct", null=True, blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_each = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    
    @property
    def total_price(self):
        return (self.price_each or Decimal("0")) * (self.quantity or 0)

    def __str__(self):
        target = self.card or self.sealed_product
        return f"Purchase: {target} x{self.quantity}"


class Sale(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, null=True, blank=True)
    sealed_product = models.ForeignKey(SealedProduct, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    platform = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales")
    
    def __str__(self):
        item = self.card or self.sealed_product
        return f"Sold {item} for ${self.price}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    
    def clean(self):
        if (self.card is None and self.sealed_product is None) or (self.card is not None and self.sealed_product is not None):
            raise ValidationError("Select either a Card OR a Sealed Product (not both).")


class TcgApisCardIndex(models.Model):
    group_id = models.IntegerField(db_index=True)
    number = models.CharField(max_length=20, db_index=True)  
    product_id = models.IntegerField()
    name = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("group_id", "number")
        
class CardCatalog(models.Model):
    # Stable identity from dataset
    catalog_id = models.CharField(max_length=80, unique=True)  # e.g. "sv3pt5-199" style id (varies by dataset)

    name = models.CharField(max_length=255)
    set_id = models.CharField(max_length=80, db_index=True)
    set_name = models.CharField(max_length=255, db_index=True)
    number = models.CharField(max_length=20, db_index=True)  # "199"
    rarity = models.CharField(max_length=100, blank=True, null=True)
    image_small = models.URLField(blank=True, null=True)
    image_large = models.URLField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["set_id", "number"]),
            models.Index(fields=["set_name", "number"]),
        ]
class MarketPrice(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, null=True, blank=True)
    sealed_product = models.ForeignKey(SealedProduct, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50, default="manual")
    date = models.DateTimeField(auto_now_add=True)


class CatalogItem(models.Model):
    """
    Represents a TCGplayer product from TCGCSV.
    Works for both sealed products and single cards.
    """
    product_id = models.IntegerField()
    group_id = models.IntegerField(null=True, blank=True)
    category_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=255)
    image_url = models.URLField(blank=True, default="")
    tcgcsv_url = models.URLField(blank=True, default="")
    card_number = models.CharField(max_length=50, blank=True, default="")
    rarity = models.CharField(max_length=80, blank=True, default="")
    printing = models.CharField(max_length=60, blank=True, default="Normal")
    is_sealed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product_id", "printing"], name="uniq_product_printing")
        ]

    def __str__(self):
        return f"{self.name} [{self.printing}] (#{self.product_id})"


class PriceSnapshot(models.Model):
    """
    Price history over time for a CatalogItem.
    """
    item = models.ForeignKey(CatalogItem, on_delete=models.CASCADE, related_name="prices")
    captured_at = models.DateTimeField()
    low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    market = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    direct_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=50, default="tcgcsv")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "captured_at"], name="uniq_item_captured_at")
        ]

