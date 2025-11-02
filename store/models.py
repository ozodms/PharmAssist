from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Customer(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    legal_name = models.CharField("Legal company name", max_length=255)
    company_reg_number = models.CharField("Company registration number", max_length=64, blank=True)
    tax_id = models.CharField("Tax ID (VAT number)",max_length=64, blank=True)
    registered_address = models.TextField("Registered company address", blank=True)
    billing_address = models.TextField(blank=True)
    delivery_address = models.TextField("Default delivery address", blank=True)
    contact_name = models.CharField("Responsible contact person", max_length=128, blank=True)
    contact_position = models.CharField("Contact person's position", max_length=128, blank=True)
    contact_email = models.EmailField("Contact persons's email", max_length=200, blank=True)
    contact_phone = models.CharField("Contact person's phone number", max_length=64, blank=True)
    bank_name = models.CharField("Bank name", max_length=200, blank=True)
    bank_account = models.CharField("Bank account / IBAN", max_length=64, blank=True)
    bank_swift = models.CharField("BIC / SWIFT", max_length=64, blank=True)

class Product(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    availability = models.PositiveIntegerField(default=0)
    package_quantity = models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to="products/", null=True, blank=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    @property
    def get_cart_total(self) -> Decimal:
       items = self.orderitem_set.select_related("product")
       return sum((item.get_total for item in items), Decimal("0.00"))

    @property
    def get_cart_items(self) -> int:
       items = self.orderitem_set.all()
       return sum((item.quantity or 0) for item in items)


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    quantity = models.PositiveIntegerField(default=1)
    date_added = models.DateTimeField(auto_now_add=True)

    @property
    def get_total(self) -> Decimal:
        price = self.product.price if (self.product and self.product.price is not None) else Decimal("0.00")
        qty = self.quantity or 0
        return price * qty


class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField(blank=True)
    contact_name = models.CharField(max_length=128, blank=True)
    contact_position = models.CharField(max_length=128, blank=True)
    contact_email = models.EmailField(max_length=200, blank=True)
    contact_phone = models.CharField(max_length=64, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
