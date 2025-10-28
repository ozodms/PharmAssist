from django.shortcuts import render, get_object_or_404
from .models import *

def store(request):
    products = Product.objects.all()
    context = {'products': products}
    return render (request, "store/store.html", context)

def cart(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}

    context = {'items': items, 'order': order}
    return render(request, "store/cart.html", context)

def checkout(request):
    if request.user.is_authenticated:
        customer = getattr(request.user, "customer", None)
        if customer:
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            items = order.orderitem_set.select_related("product").all()
        else:
            items = []
            order = {'get_cart_total': 0, 'get_cart_items': 0}
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}

    context = {'items': items, 'order': order}
    return render(request, "store/checkout.html", context)

def order_confirm(request):
    context = {}
    return render(request, "store/order_confirmation.html", context)

def order_item(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "store/order_item.html", {"product": product})
