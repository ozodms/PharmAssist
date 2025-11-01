from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import *
import json

def get_cart_context(request):
    items = []
    total = 0
    total_items = 0

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        for oi in order.orderitem_set.select_related("product").all():
            subtotal = oi.product.price * oi.quantity
            items.append({
                "product": oi.product,
                "quantity": oi.quantity,
                "subtotal": subtotal,
            })
            total += subtotal
            total_items += oi.quantity

        return {
            "items": items,
            "total": total,
            "total_items": total_items,
            "order": order,
            "is_db": True,
        }

    cart_data = request.session.get("cart", {})
    for pid, qty in cart_data.items():
        product = get_object_or_404(Product, id=pid)
        subtotal = product.price * qty
        items.append({
            "product": product,
            "quantity": qty,
            "subtotal": subtotal,
        })
        total += subtotal
        total_items += qty

    return {
        "items": items,
        "total": total,
        "total_items": total_items,
        "order": None,
        "is_db": False,
    }


def store(request):
    products = Product.objects.all()

    cart_ctx = get_cart_context(request)

    context = {
        'products': products,
        'cartItems': cart_ctx['total_items'],
    }
    return render(request, 'store/store.html', context)


def cart(request):
    ctx = get_cart_context(request)
    return render(request, "store/cart.html", ctx)


def checkout(request):
    ctx = get_cart_context(request)
    return render(request, "store/checkout.html", ctx)


def updateItem(request):

    try:
        data = json.loads(request.body or "{}")
        product_id = int(data.get('productId'))
        action = data.get('action')
        product = get_object_or_404(Product, id=product_id)
    except Exception:
        return JsonResponse({'error': 'Bad request'}, status=400)

    if action not in ('add', 'remove', 'clear'):
        return JsonResponse({'error': 'Unknown action'}, status=400)

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        if action == 'clear':
            OrderItem.objects.filter(order=order, product=product).delete()
            return JsonResponse({'ok': True})

        order_item, created = OrderItem.objects.get_or_create(order=order, product=product)

        if action == 'add':
            if created:
                order_item.quantity = 1
            else:
                if order_item.quantity < product.availability:
                        order_item.quantity += 1
            order_item.save()

        elif action == 'remove':
            order_item.quantity -= 1
            if order_item.quantity <= 0:
                order_item.delete()
            else:
                order_item.save()

        return JsonResponse({'ok': True})

    cart = request.session.get('cart', {})
    pid = str(product.id)
    qty = int(cart.get(pid, 0))

    if action == 'clear':
        cart.pop(pid, None)
        request.session['cart'] = cart
        return JsonResponse({'ok': True})

    if action == 'add':
        qty = min(qty + 1, product.availability)
    elif action == 'remove':
        qty -= 1

    if qty <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = qty

    request.session['cart'] = cart

    return JsonResponse({'ok': True})


def order_confirm(request):
    return render(request, "store/order_confirmation.html")


def order_item(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "store/order_item.html", {"product": product})

@require_POST
def set_quantity(request, pk):
    product = get_object_or_404(Product, pk=pk)

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    qty = max(1, min(qty, product.availability))

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
        item, _ = OrderItem.objects.get_or_create(order=order, product=product)
        item.quantity = qty
        item.save()
        return JsonResponse({"ok": True, "qty": qty})

    cart = request.session.get("cart", {})
    cart[str(product.id)] = qty
    request.session["cart"] = cart

    return JsonResponse({"ok": True, "qty": qty})
