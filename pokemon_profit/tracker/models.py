from django.db import models
from django.forms import ValidationError

class Card(models.Model):
    name = models.CharField(max_length=100)
    set_name = models.CharField(max_length=100)
    card_number = models.CharField(max_length=20, blank=True)
    condition = models.CharField(max_length = 20, blank=True)
    tcgapis_group_id = models.IntegerField(null=True, blank=True)
    tcgapis_product_id = models.IntegerField(null=True, blank=True)
    ptcg_id = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    ptcg_set_id = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    ptcg_set_name = models.CharField(max_length=200, blank=True, null=True)
    ptcg_number = models.CharField(max_length=20, blank=True, null=True)
    ptcg_rarity = models.CharField(max_length=80, blank=True, null=True)
    ptcg_image_small = models.URLField(blank=True, null=True)
    ptcg_image_large = models.URLField(blank=True, null=True)
    catalog = models.ForeignKey("CardCatalog", null=True, blank=True, on_delete=models.SET_NULL)
    catalog_id_str = models.CharField(max_length=80, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.set_name})"
    
    @property
    def total_spent(self):
        return sum(p.price for p in self.purchase_set.all())

    @property
    def total_sales(self):
        return sum(s.price for s in self.sale_set.all())

    @property
    def realized_profit(self):
        return self.total_sales - self.total_spent

    @property
    def current_market_value(self):
        latest_price = self.marketprice_set.order_by('-date').first()
        return latest_price.price if latest_price else 0

    @property
    def unrealized_profit(self):
        return self.current_market_value - self.total_spent

class SealedProduct(models.Model):
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=50)
    set_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.name} - {self.product_type}"
    
    @property
    def total_spent(self):
        return sum(p.price for p in self.purchase_set.all())

    @property
    def total_sales(self):
        return sum(s.price for s in self.sale_set.all())

    @property
    def realized_profit(self):
        return self.total_sales - self.total_spent

    @property
    def current_market_value(self):
        latest_price = self.marketprice_set.order_by('-date').first()
        return latest_price.price if latest_price else 0

    @property
    def unrealized_profit(self):
        return self.current_market_value - self.total_spent
    
class Purchase(models.Model):
    card = models.ForeignKey('Card', on_delete=models.CASCADE, null=True, blank=True)
    sealed_product = models.ForeignKey('SealedProduct', on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    source = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        item = self.card or self.sealed_product
        return f"Purchased {item} for ${self.price}"
    
    def save(self, *args, **kwargs):
        self.full_clean()  
        return super().save(*args, **kwargs)
    
    def clean(self):
        if (self.card is None and self.sealed_product is None) or (self.card is not None and self.sealed_product is not None):
            raise ValidationError("Select either a Card OR a Sealed Product (not both).")

class Sale(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, null=True, blank=True)
    sealed_product = models.ForeignKey(SealedProduct, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    platform = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        item = self.card or self.sealed_product
        return f"Sold {item} for ${self.price}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    
    def clean(self):
        if (self.card is None and self.sealed_product is None) or (self.card is not None and self.sealed_product is not None):
            raise ValidationError("Select either a Card OR a Sealed Product (not both).")


class MarketPrice(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, null=True, blank=True)
    sealed_product = models.ForeignKey(SealedProduct, on_delete=models.CASCADE, null=True, blank=True)
    source = models.CharField(max_length=50)  # TCGplayer, PriceCharting
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        item = self.card or self.sealed_product
        return f"{item} @ {self.price} ({self.source})"

class TcgApisCardIndex(models.Model):
    group_id = models.IntegerField(db_index=True)
    number = models.CharField(max_length=20, db_index=True)  # "199"
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
