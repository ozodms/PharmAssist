from django.shortcuts import render

def store(request):
    context = {}
    return render (request, "store/store.html", context)

def cart(request):
    context = {}
    return render (request, "store/cart.html", context)

def checkout(request):
    context = {}
    return render (request, "store/checkout.html", context)

def order_confirm(request):
    context = {}
    return render(request, "store/order_confirmation.html", context)

def order_item(request):
    context = {}
    return render(request, "store/order_item.html", context)
