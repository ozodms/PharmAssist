from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
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

def _attach_session_cart_to_order(request, customer):
    cart_data = request.session.get("cart", {})
    if not cart_data:
        return

    order, _ = Order.objects.get_or_create(customer=customer, complete=False)

    for pid, qty in cart_data.items():
        product = get_object_or_404(Product, id=pid)
        item, _ = OrderItem.objects.get_or_create(order=order, product=product)
        item.quantity = qty
        item.save()

    request.session["cart"] = {}
    request.session.modified = True


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


@transaction.atomic
def checkout(request):
    if request.user.is_authenticated:
        ctx = get_cart_context(request)
        return render(request, "store/checkout.html", ctx)

    if request.method == "GET":
        ctx = get_cart_context(request)
        return render(request, "store/checkout.html", ctx)

    legal_name = request.POST.get("legal_name", "").strip()
    company_reg_number = request.POST.get("company_reg_number", "").strip()
    tax_id = request.POST.get("tax_id", "").strip()
    registered_address = request.POST.get("registered_address", "").strip()
    billing_address = request.POST.get("billing_address", "").strip()
    delivery_address = request.POST.get("delivery_address", "").strip()

    contact_name = request.POST.get("contact_name", "").strip()
    contact_position = request.POST.get("contact_position", "").strip()
    contact_email = request.POST.get("contact_email", "").strip()
    contact_phone = request.POST.get("contact_phone", "").strip()

    bank_name = request.POST.get("bank_name", "").strip()
    bank_account = request.POST.get("bank_account", "").strip()
    bank_swift = request.POST.get("bank_swift", "").strip()

    password1 = request.POST.get("password1", "")
    password2 = request.POST.get("password2", "")

    # validation
    errors = []
    required_fields = [
        legal_name, company_reg_number, tax_id,
        registered_address,
        contact_name, contact_position, contact_email, contact_phone,
        bank_name, bank_account, bank_swift,
        password1, password2
    ]
    if any(not f for f in required_fields):
        errors.append("Please fill in all required fields.")
    if password1 != password2:
        errors.append("Passwords do not match.")
    if len(password1) < 8:
        errors.append("Password must be at least 8 characters.")
    if User.objects.filter(username=tax_id).exists():
        errors.append("An account with this Tax ID already exists. Please log in.")

    if errors:
        ctx = get_cart_context(request)
        ctx["error"] = errors[0]
        return render(request, "store/checkout.html", ctx)

    user = User.objects.create_user(
        username=tax_id,
        password=password1,
        email=contact_email or ""
    )

    customer, _ = Customer.objects.get_or_create(user=user)
    customer.legal_name = legal_name
    customer.company_reg_number = company_reg_number
    customer.tax_id = tax_id
    customer.registered_address = registered_address
    customer.billing_address = billing_address
    customer.delivery_address = delivery_address
    customer.contact_name = contact_name
    customer.contact_position = contact_position
    customer.contact_email = contact_email
    customer.contact_phone = contact_phone
    customer.bank_name = bank_name
    customer.bank_account = bank_account
    customer.bank_swift = bank_swift
    customer.save()

    _attach_session_cart_to_order(request, customer)
    login(request, user)
    return redirect("order")


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

def login_views(request):
    if request.user.is_authenticated:
        return redirect('store')

    if request.method == 'POST':
        tax_id = request.POST.get('tax_id')
        password = request.POST.get('password')
        user = authenticate(request, username=tax_id, password=password)
        if user is not None:
            login(request, user)
            return redirect('store')
        else:
            return render(request, 'store/login.html', {
                'error': 'Wrong Tax ID or password.',
            })

    return render(request, 'store/login.html')


def register_views(request):
    if request.method == 'POST':
        legal_name = request.POST.get('legal_name', '').strip()
        tax_id = request.POST.get('tax_id', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        company_reg_number = request.POST.get('company_reg_number', '').strip()
        registered_address = request.POST.get('registered_address', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        bank_account = request.POST.get('bank_account', '').strip()
        bank_swift = request.POST.get('bank_swift', '').strip()
        required_fields = [
            legal_name, tax_id, email, password1, password2,
            company_reg_number, registered_address, contact_phone,
            bank_name, bank_account, bank_swift,
        ]
        if any(not f for f in required_fields):
            return render(request, 'store/register.html', {
                'error': 'Please fill in all required fields.',
            })

        if password1 != password2:
            return render(request, 'store/register.html', {
                'error': 'Passwords do not match.',
            })

        if User.objects.filter(username=tax_id).exists():
            return render(request, 'store/register.html', {
                'error': 'A user with this Tax ID already exists.',
            })

        user = User.objects.create_user(
            username=tax_id,
            email=email,
            password=password1,
        )

        Customer.objects.create(
            user=user,
            legal_name=legal_name,
            company_reg_number=company_reg_number,
            tax_id=tax_id,
            registered_address=registered_address,
            contact_email=email,
            contact_phone=contact_phone,
            bank_name=bank_name,
            bank_account=bank_account,
            bank_swift=bank_swift,
        )

        auth_user = authenticate(request, username=tax_id, password=password1)
        if auth_user:
            login(request, auth_user)
            return redirect('store')
        return redirect('login')

    return render(request, 'store/register.html')


def logout_views(request):
    logout(request)
    return redirect('store')

@login_required
def profile_views(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        customer.legal_name = request.POST.get('legal_name', '').strip()
        customer.company_reg_number = request.POST.get('company_reg_number', '').strip()
        customer.registered_address = request.POST.get('registered_address', '').strip()
        customer.billing_address = request.POST.get('billing_address', '').strip()
        customer.delivery_address = request.POST.get('delivery_address', '').strip()
        customer.contact_name = request.POST.get('contact_name', '').strip()
        customer.contact_position = request.POST.get('contact_position', '').strip()
        customer.contact_email = request.POST.get('contact_email', '').strip()
        customer.contact_phone = request.POST.get('contact_phone', '').strip()
        customer.bank_name = request.POST.get('bank_name', '').strip()
        customer.bank_account = request.POST.get('bank_account', '').strip()
        customer.bank_swift = request.POST.get('bank_swift', '').strip()
        customer.save()
        return render(request, 'store/profile.html', {
            'customer': customer,
            'saved': True,
        })

    return render(request, 'store/profile.html', {
        'customer': customer,
    })
