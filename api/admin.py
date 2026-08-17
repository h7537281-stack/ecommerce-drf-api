from django.contrib import admin

from .models import (
    Category, Product, ProductImage, 
    Customer, Address, 
    Cart, CartItem, 
    Order, OrderItem, 
    Review
)

# ==========================================
# 1. Inlines (الجداول المضمنة):لموديلات الرئيسية والمستقلة التي تحتوي على بيانات كثيرة تُدار عبر ModelAdmin خاص بها، بينما الموديلات التابعة الخفيفة تُدمَج كـ TabularInline داخل صفحة موديلها الأب.
# ==========================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # عدد الصفوف الفارغة المتاحة لإضافة صور جديدة فوراً


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    min_num = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


# 2. Model Admin Classes (تنسيق صفحات التحكم)
# ==========================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit_price', 'inventory', 'category']
    list_editable = ['unit_price', 'inventory']  # إمكانية التعديل السريع مباشرة من الجدول
    list_per_page = 10
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'description']
    list_filter = ['category']
    inlines = [ProductImageInline]  # إمكانية رفع صور المنتج مباشرة من صفحة المنتج نفسه


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone']
    list_select_related = ['user']
    search_fields = ['user__first_name', 'user__last_name', 'phone']

    def first_name(self, customer):
        return customer.user.first_name

    def last_name(self, customer):
        return customer.user.last_name


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['customer', 'city', 'street']
    search_fields = ['city', 'street']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    inlines = [CartItemInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'payment_status', 'placed_at']
    list_editable = ['payment_status']
    inlines = [OrderItemInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'date']
    search_fields = ['product__title', 'name']
