from django.contrib import admin
from .models import Card, SealedProduct, Purchase, Sale, CatalogItem, PriceSnapshot


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "set_name",
        "card_number",
        "printing",
        "catalog_item",
        "current_market_value",
        "total_spent",
        "total_sales",
        "realized_profit",
        "unrealized_profit",
    )
    search_fields = ("name", "set_name", "card_number")
    list_filter = ("printing",)
    list_select_related = ("catalog_item",)


@admin.register(SealedProduct)
class SealedProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "set_name",
        "quantity",
        "catalog_item",
        "current_market_value",
        "total_spent",
        "total_sales",
        "realized_profit",
        "unrealized_profit",
    )
    search_fields = ("name", "set_name")
    list_select_related = ("catalog_item",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "item",
        "quantity",
        "price_each",
        "total_price",
    )
    list_filter = ("date",)
    search_fields = ("card__name", "sealed_product__name", "card__set_name", "sealed_product__set_name")
    date_hierarchy = "date"
    list_select_related = ("card", "sealed_product")

    @admin.display(description="Item")
    def item(self, obj):
        return obj.card or obj.sealed_product


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("date", "item", "price", "platform")
    list_filter = ("platform", "date")
    search_fields = ("card__name", "sealed_product__name", "platform")
    date_hierarchy = "date"
    list_select_related = ("card", "sealed_product")

    @admin.display(description="Item")
    def item(self, obj):
        return obj.card or obj.sealed_product


admin.site.register(CatalogItem)
admin.site.register(PriceSnapshot)
