from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from .models import *
import json
from decimal import Decimal
from json import JSONDecodeError


def get_cart_context(request):
    items, total, total_items = [], Decimal("0.00"), 0

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        for oi in order.orderitem_set.select_related("product"):
            if not oi.product:
                continue
            subtotal = oi.product.price * oi.quantity
            items.append(
                {"product": oi.product, "quantity": oi.quantity, "subtotal": subtotal}
            )
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
    if not cart_data:
        return {
            "items": [],
            "total": total,
            "total_items": 0,
            "order": None,
            "is_db": False,
        }

    pids = [int(pid) for pid in cart_data.keys()]
    products = Product.objects.in_bulk(pids)
    for pid_str, qty in cart_data.items():
        pid = int(pid_str)
        product = products.get(pid)
        if not product:
            continue
        subtotal = product.price * qty
        items.append({"product": product, "quantity": qty, "subtotal": subtotal})
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

    pids = [int(pid) for pid in cart_data.keys()]
    products = Product.objects.in_bulk(pids)

    for pid_str, qty in cart_data.items():
        product = products.get(int(pid_str))
        if not product:
            continue
        item, _ = OrderItem.objects.get_or_create(order=order, product=product)
        new_qty = min((item.quantity or 0) + int(qty), product.availability)
        if new_qty <= 0:
            item.delete()
        else:
            item.quantity = new_qty
            item.save()

    request.session["cart"] = {}
    request.session.modified = True


def store(request):
    products = Product.objects.all()

    cart_ctx = get_cart_context(request)

    context = {
        "products": products,
        "cartItems": cart_ctx["total_items"],
    }
    return render(request, "store/store.html", context)


def cart(request):
    ctx = get_cart_context(request)
    return render(request, "store/cart.html", ctx)

@transaction.atomic
def checkout(request):
    ctx = get_cart_context(request)
    if request.method == "GET":
        return render(request, "store/checkout.html", ctx)

    if request.user.is_authenticated:
        return render(request, "store/checkout.html", ctx)

    fields = {k: request.POST.get(k, "").strip() for k in [
        "legal_name","company_reg_number","tax_id","registered_address",
        "billing_address","delivery_address","contact_name","contact_position",
        "contact_email","contact_phone","bank_name","bank_account","bank_swift",
        "password1","password2",
    ]}

    errors = []
    required = ["legal_name","company_reg_number","tax_id","registered_address",
                "contact_name","contact_position","contact_email","contact_phone",
                "bank_name","bank_account","bank_swift","password1","password2"]
    if any(not fields[k] for k in required):
        errors.append("Please fill in all required fields.")
    if fields["password1"] != fields["password2"]:
        errors.append("Passwords do not match.")
    if len(fields["password1"]) < 8:
        errors.append("Password must be at least 8 characters.")
    if User.objects.filter(username=fields["tax_id"]).exists():
        errors.append("An account with this Tax ID already exists. Please log in.")

    if errors:
        ctx["errors"] = errors
        return render(request, "store/checkout.html", ctx)

    with transaction.atomic():
        user = User.objects.create_user(
            username=fields["tax_id"],
            password=fields["password1"],
            email=fields["contact_email"] or ""
        )
        customer, _ = Customer.objects.get_or_create(user=user)
        customer.legal_name = fields["legal_name"]
        customer.company_reg_number = fields["company_reg_number"]
        customer.tax_id = fields["tax_id"]
        customer.registered_address = fields["registered_address"]
        customer.billing_address = fields["billing_address"]
        customer.delivery_address = fields["delivery_address"]
        customer.contact_name = fields["contact_name"]
        customer.contact_position = fields["contact_position"]
        customer.contact_email = fields["contact_email"]
        customer.contact_phone = fields["contact_phone"]
        customer.bank_name = fields["bank_name"]
        customer.bank_account = fields["bank_account"]
        customer.bank_swift = fields["bank_swift"]
        customer.save()

        _attach_session_cart_to_order(request, customer)

    transaction.on_commit(lambda: login(request, user))
    return redirect("order")

def updateItem(request):
    try:
        data = json.loads(request.body)
        product_id = int(data.get('productId'))
        action = data.get('action')
    except (JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Bad request'}, status=400)

    if action not in ('add', 'remove', 'clear'):
        return JsonResponse({'error': 'Unknown action'}, status=400)

    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        if action == 'clear':
            OrderItem.objects.filter(order=order, product=product).delete()
            return JsonResponse({'ok': True})

        oi, created = OrderItem.objects.get_or_create(order=order, product=product)

        if action == 'add':
            new_qty = min((oi.quantity or 0) + 1, product.availability)
            if new_qty <= 0:
                oi.delete()
            else:
                oi.quantity = new_qty
                oi.save()

        elif action == 'remove':
            new_qty = (oi.quantity or 0) - 1
            if new_qty <= 0:
                oi.delete()
            else:
                oi.quantity = min(new_qty, product.availability)
                oi.save()

        return JsonResponse({'ok': True})

    # session cart
    cart = request.session.get('cart', {})
    pid = str(product.id)
    qty = int(cart.get(pid, 0))

    if action == 'clear':
        cart.pop(pid, None)
    elif action == 'add':
        cart[pid] = min(qty + 1, product.availability)
    elif action == 'remove':
        new_qty = qty - 1
        if new_qty <= 0:
            cart.pop(pid, None)
        else:
            cart[pid] = min(new_qty, product.availability)

    request.session['cart'] = cart
    request.session.modified = True
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

    qty = max(0, min(qty, product.availability))

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user)
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
        if qty <= 0:
            OrderItem.objects.filter(order=order, product=product).delete()
            return JsonResponse({"ok": True, "qty": 0})
        item, _ = OrderItem.objects.get_or_create(order=order, product=product)
        item.quantity = qty
        item.save()
        return JsonResponse({"ok": True, "qty": qty})

    cart = request.session.get("cart", {})
    if qty <= 0:
        cart.pop(str(product.id), None)
    else:
        cart[str(product.id)] = qty
    request.session["cart"] = cart
    request.session.modified = True
    return JsonResponse({"ok": True, "qty": qty})


def login_views(request):
    if request.user.is_authenticated:
        return redirect("store")

    if request.method == "POST":
        tax_id = request.POST.get("tax_id")
        password = request.POST.get("password")
        user = authenticate(request, username=tax_id, password=password)
        if user is not None:
            login(request, user)
            return redirect("store")
        else:
            return render(
                request,
                "store/login.html",
                {
                    "error": "Wrong Tax ID or password.",
                },
            )

    return render(request, "store/login.html")


def register_views(request):
    if request.method == "POST":
        legal_name = request.POST.get("legal_name", "").strip()
        tax_id = request.POST.get("tax_id", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        company_reg_number = request.POST.get("company_reg_number", "").strip()
        registered_address = request.POST.get("registered_address", "").strip()
        contact_phone = request.POST.get("contact_phone", "").strip()
        bank_name = request.POST.get("bank_name", "").strip()
        bank_account = request.POST.get("bank_account", "").strip()
        bank_swift = request.POST.get("bank_swift", "").strip()
        required_fields = [
            legal_name,
            tax_id,
            email,
            password1,
            password2,
            company_reg_number,
            registered_address,
            contact_phone,
            bank_name,
            bank_account,
            bank_swift,
        ]
        if any(not f for f in required_fields):
            return render(
                request,
                "store/register.html",
                {
                    "error": "Please fill in all required fields.",
                },
            )

        if password1 != password2:
            return render(
                request,
                "store/register.html",
                {
                    "error": "Passwords do not match.",
                },
            )

        if User.objects.filter(username=tax_id).exists():
            return render(
                request,
                "store/register.html",
                {
                    "error": "A user with this Tax ID already exists.",
                },
            )

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
            return redirect("store")
        return redirect("login")

    return render(request, "store/register.html")


def logout_views(request):
    logout(request)
    return redirect("store")


@login_required
def profile_views(request):
    customer, _ = Customer.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        for field in [
            'legal_name','company_reg_number','registered_address','billing_address','delivery_address',
            'contact_name','contact_position','contact_email','contact_phone',
            'bank_name','bank_account','bank_swift'
        ]:
            setattr(customer, field, request.POST.get(field, '').strip())
        customer.save()
        return redirect('profile')  # PRG

    return render(request, 'store/profile.html', {'customer': customer})


def home(request):
    return render(request, "store/home.html", {})
