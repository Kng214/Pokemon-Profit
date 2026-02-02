from django.contrib import admin
from .models import Card, SealedProduct, Purchase, Sale

admin.site.register(Card)
admin.site.register(SealedProduct)
admin.site.register(Purchase)
admin.site.register(Sale)

