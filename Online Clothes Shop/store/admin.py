from django.contrib import admin
from django import forms
from .models import Product, ProductVariant, Order, OrderItem, SIZES

admin.site.site_header = "CLOTHE Admin Panel"
admin.site.site_title = "CLOTHE Admin"
admin.site.index_title = "Welcome to CLOTHE Management"

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('size', 'stock')
    readonly_fields = ('size',)
    can_delete = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('id')

    def has_add_permission(self, request, obj=None):
        return False

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'price')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'total_stock', 'stock_status')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    list_editable = ('price',)
    ordering = ('category', 'name')
    inlines = [ProductVariantInline]

    def total_stock(self, obj):
        return obj.total_stock()
    total_stock.short_description = 'Total Stock'

    def stock_status(self, obj):
        stock = obj.total_stock()
        if stock == 0:
            return '❌ Out of Stock'
        elif stock <= 5:
            return f'⚠️ Low ({stock})'
        return f'✅ In Stock ({stock})'
    stock_status.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Make sure all 5 sizes exist for existing products
        for size in SIZES:
            ProductVariant.objects.get_or_create(product=obj, size=size)
    def response_add(self, request, obj, post_url_continue=None):
      
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(
            reverse('admin:store_product_change', args=[obj.pk])
        )

    def response_change(self, request, obj):
        # After editing, redirect to management page
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('/management/')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'email', 'total_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer_name', 'email')
    readonly_fields = ('customer_name', 'email', 'address', 'total_price', 'created_at', 'user')
    ordering = ('-created_at',)
    inlines = [OrderItemInline]