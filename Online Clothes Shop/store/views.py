from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .models import Product, ProductVariant, Order, OrderItem, Cart, CartItem, Contact
from django.contrib.auth.models import User
from .forms import ProductForm, VariantFormSet, RegisterForm


def home(request):
    products = Product.objects.all()
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')

    if query:
        products = products.filter(name__icontains=query)
    if category:
        products = products.filter(category=category)

    recommendations = []
    if request.user.is_authenticated and not query and not category:
        has_orders = Order.objects.filter(user=request.user).exists()
        if has_orders:
            recommendations = get_recommendations(request.user)

    return render(request, 'store/home.html', {
        'products': products,
        'query': query,
        'category': category,
        'recommendations': recommendations,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    size_order = {'M': 1, 'L': 2, 'XL': 3, '2XL': 4, '3XL': 5}
    variants = sorted(product.variants.all(), key=lambda v: size_order.get(v.size, 99))
    recommendations = get_recommendations(request.user, current_product=product)
    return render(request, 'store/detail.html', {
        'product': product,
        'variants': variants,
        'recommendations': recommendations,
    })


# ========================
# CART
# ========================

@login_required(login_url='/login/')
def add_to_cart(request, pk):
    variant_id = request.POST.get('variant_id')
    if not variant_id:
        messages.error(request, 'Please select a size!')
        return redirect('detail', pk=pk)

    product = get_object_or_404(Product, pk=pk)
    variant = get_object_or_404(ProductVariant, pk=variant_id)

    if variant.stock <= 0:
        messages.error(request, 'Out of stock!')
        return redirect('detail', pk=pk)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)

    variant.stock -= 1
    variant.save()

    if not created:
        cart_item.quantity += 1
    else:
        cart_item.quantity = 1
    cart_item.save()

    messages.success(request, 'Added to cart!')
    return redirect('detail', pk=pk)


@login_required(login_url='/login/')
def cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    items = []
    total = 0
    for item in cart_items:
        subtotal = item.product.price * item.quantity
        total += subtotal
        items.append({'item': item, 'subtotal': subtotal})
    return render(request, 'store/cart.html', {'items': items, 'total': total})


@login_required(login_url='/login/')
def remove_from_cart(request, key):
    item = get_object_or_404(CartItem, pk=key)
    item.variant.stock += item.quantity
    item.variant.save()
    item.delete()
    messages.success(request, 'Item removed.')
    return redirect('cart')


@login_required(login_url='/login/')
def update_cart(request, key):
    item = get_object_or_404(CartItem, pk=key)
    new_qty = int(request.POST.get('quantity', 1))
    if new_qty < 1:
        item.variant.stock += item.quantity
        item.variant.save()
        item.delete()
        return redirect('cart')
    diff = new_qty - item.quantity
    if diff > 0:
        if item.variant.stock < diff:
            messages.error(request, f'Only {item.variant.stock} left!')
            return redirect('cart')
        item.variant.stock -= diff
    elif diff < 0:
        item.variant.stock += abs(diff)
    item.variant.save()
    item.quantity = new_qty
    item.save()
    return redirect('cart')


# ========================
# CHECKOUT
# ========================

@login_required(login_url='/login/')
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        return redirect('cart')
    total = sum(item.product.price * item.quantity for item in cart_items)
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        email = request.POST.get('email')
        address = request.POST.get('address')
        order = Order.objects.create(
            user=request.user,
            customer_name=customer_name,
            email=email,
            address=address,
            total_price=total,
            is_paid=False
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                price=item.product.price
            )
        cart_items.delete()
        messages.success(request, 'Order placed successfully!')
        return redirect('order_confirmation', pk=order.pk)
    return render(request, 'store/checkout.html', {'items': cart_items, 'total': total})


def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'store/confirmation.html', {'order': order, 'order_items': items})


# ========================
# AUTH
# ========================

def register_view(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Account created! Welcome, {user.username}!')
        return redirect('home')
    return render(request, 'store/register.html', {'form': form})


def login_view(request):
    form = AuthenticationForm(data=request.POST or None)
    if form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('home')
    return render(request, 'store/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required(login_url='/login/')
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})


@login_required(login_url='/login/')
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'store/order_detail.html', {'order': order, 'items': items})


@login_required(login_url='/login/')
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/profile.html', {'orders': orders})


@login_required(login_url='/login/')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'store/change_password.html', {'form': form})


# ========================
# MANAGEMENT
# ========================

@staff_member_required(login_url='/login/')
def management(request):
    products = Product.objects.all()
    orders = Order.objects.all().order_by('-created_at')
    total_products = products.count()
    total_orders = orders.count()
    # Revenue only from completed orders
    total_revenue = sum(
    o.total_price for o in orders if o.status == 'completed')
    low_stock = [p for p in products if p.total_stock() <= 3]
    unread_count = Contact.objects.filter(is_read=False).count()
    return render(request, 'store/management.html', {
        'products': products,
        'orders': orders,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'low_stock': low_stock,
        'unread_count': unread_count,
    })


@staff_member_required(login_url='/login/')
def admin_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'store/admin_order_detail.html', {'order': order, 'items': items})


@staff_member_required(login_url='/login/')
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        status = request.POST.get('status')

        valid_statuses = ['received', 'confirmed', 'delivering']

        if status in valid_statuses:
            order.status = status

            if status == 'completed':
                order.is_paid = True

            order.save()
            messages.success(request, f'Order #{order.id} updated!')

    return redirect('admin_order_detail', pk=pk)


@staff_member_required(login_url='/login/')
def complete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.status = 'completed'
        order.is_paid = True
        order.save()
        messages.success(request, f'Order #{order.id} marked as completed! Revenue updated.')
    return redirect('admin_order_detail', pk=pk)


@staff_member_required(login_url='/login/')
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if order.status != 'cancelled':
        for item in order.orderitem_set.all():
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

        order.status = 'cancelled'
        order.save()

        messages.success(request, f'Order #{pk} cancelled and stock restored!')

    return redirect('management')


@staff_member_required(login_url='/login/')
def delete_order_permanently(request, pk):
    order = get_object_or_404(Order, pk=pk)
    # Only allow deleting cancelled orders
    if order.status == 'cancelled':
        order.delete()
        messages.success(request, f'Order #{pk} permanently deleted!')
    return redirect('management')


@staff_member_required(login_url='/login/')
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, 'Product deleted!')
    return redirect('management')


@staff_member_required(login_url='/login/')
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        formset = VariantFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            product = form.save()
            variants = formset.save(commit=False)
            for variant in variants:
                variant.product = product
                variant.save()
            messages.success(request, 'Product created!')
            return redirect('management')
    else:
        form = ProductForm()
        formset = VariantFormSet()
    return render(request, 'store/add_product.html', {'form': form, 'formset': formset})


@staff_member_required(login_url='/login/')
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = VariantFormSet(request.POST, instance=product) 

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save() 
            messages.success(request, 'Product updated!')
            return redirect('management')
        else:
            print(form.errors)
            print(formset.errors)

    else:
        form = ProductForm(instance=product)
        formset = VariantFormSet(instance=product)
    return render(request, 'store/add_product.html', {
        'form': form,
        'formset': formset,
        'editing': True
    })

# ========================
# CONTACT
# ========================

@login_required(login_url='/login/')
def contact(request):
    if request.method == 'POST':
        Contact.objects.create(
            user=request.user,
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message')
        )
        messages.success(request, 'Your message has been sent!')
        return redirect('contact')
    return render(request, 'store/contact.html')


@staff_member_required(login_url='/login/')
def contact_messages(request):
    contacts = Contact.objects.all().order_by('-created_at')
    return render(request, 'store/contact_messages.html', {'contacts': contacts})


@staff_member_required(login_url='/login/')
def mark_contact_read(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.is_read = True
    contact.save()
    return redirect('contact_messages')


# ========================
# ACCOUNT MANAGEMENT
# ========================

@staff_member_required(login_url='/login/')
def manage_accounts(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'store/manage_accounts.html', {'users': users})


@staff_member_required(login_url='/login/')
def create_account(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        role = request.POST.get('role')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('create_account')
        user = User.objects.create_user(username=username, email=email, password=password)
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        messages.success(request, f'Account "{username}" created!')
        return redirect('manage_accounts')
    return render(request, 'store/create_account.html')


@staff_member_required(login_url='/login/')
def delete_account(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('manage_accounts')
    user.delete()
    messages.success(request, 'Account deleted!')
    return redirect('manage_accounts')


@staff_member_required(login_url='/login/')
def toggle_admin(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot change your own role!')
        return redirect('manage_accounts')
    user.is_staff = not user.is_staff
    user.is_superuser = user.is_staff
    user.save()
    role = 'Admin' if user.is_staff else 'User'
    messages.success(request, f'{user.username} is now {role}!')
    return redirect('manage_accounts')


@staff_member_required(login_url='/login/')
def admin_change_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        password = request.POST.get('password')
        user.set_password(password)
        user.save()
        messages.success(request, f'Password for {user.username} changed!')
        return redirect('manage_accounts')
    return render(request, 'store/admin_change_password.html', {'target_user': user})


# ========================
# RECOMMENDATIONS
# ========================

def get_recommendations(user, current_product=None, limit=4):
    from collections import defaultdict
    from django.db.models import Count

    all_orders = Order.objects.prefetch_related('orderitem_set__product').all()
    product_buyers = defaultdict(set)
    user_products = defaultdict(set)

    for order in all_orders:
        for item in order.orderitem_set.all():
            product_buyers[item.product.id].add(order.user_id)
            user_products[order.user_id].add(item.product.id)

    if user.is_authenticated:
        user_bought = user_products.get(user.id, set())
        similar_users = defaultdict(int)
        for product_id in user_bought:
            for buyer_id in product_buyers[product_id]:
                if buyer_id != user.id:
                    similar_users[buyer_id] += 1

        recommended_ids = defaultdict(int)
        for similar_user_id, score in similar_users.items():
            for product_id in user_products[similar_user_id]:
                if product_id not in user_bought:
                    if current_product is None or product_id != current_product.id:
                        recommended_ids[product_id] += score

        sorted_ids = sorted(recommended_ids, key=recommended_ids.get, reverse=True)
        if sorted_ids:
            recommended = []
            for pid in sorted_ids[:limit]:
                try:
                    p = Product.objects.get(pk=pid)
                    if p.total_stock() > 0:
                        recommended.append(p)
                except Product.DoesNotExist:
                    pass
            if recommended:
                return recommended

    user_bought_ids = user_products.get(user.id if user.is_authenticated else 0, set())
    popular = Product.objects.annotate(
        order_count=Count('orderitem')
    ).exclude(id__in=user_bought_ids).order_by('-order_count')
    if current_product:
        popular = popular.exclude(pk=current_product.pk)
    return list(popular[:limit])