from django.contrib import admin
from .models import *
from .models import Product, Customer, Order, OrderItem, ShippingAddress

admin.site.register(ShippingAddress)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "country", "price", "availability", "package_quantity")
    list_display_links = ("name",)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "company_reg_number", "contact_name", "contact_email", "contact_phone")
    list_display_links = ("legal_name",)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("product", "order", "quantity", "date_added")
    list_display_links = ("product", "order")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("customer", "transaction_id", "date_ordered", "complete")
    list_display_links = ("customer", "transaction_id")
