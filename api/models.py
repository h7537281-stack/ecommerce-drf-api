import uuid
from django.db import models 
from django.conf import settings
from django.core.validators import MinValueValidator , MaxValueValidator
from django.utils.text import slugify

class Category(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان التصنيف")
    slug = models.SlugField()

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"

    def __str__(self):
        return self.title


class Product(models.Model):
    title = models.CharField(max_length=255, verbose_name="اسم المنتج")
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name="وصف المنتج")
    unit_price=models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(1)],verbose_name="السعر")
    inventory = models.PositiveIntegerField(verbose_name="المخزون")
    category=models.ForeignKey(Category,on_delete=models.PROTECT,related_name='products',verbose_name="التصنيف")
    image = models.ImageField(upload_to='api/images', null=True, blank=True, verbose_name="صورة المنتج")
    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.title



class Customer(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=("المستخدم"), on_delete=models.CASCADE, related_name='customer')
    phone = models.CharField(max_length=255, blank=True, null=True, verbose_name="رقم الهاتف")
    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Address(models.Model):
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='addresses',
        verbose_name="العميل"
    )
    street = models.CharField(max_length=255, verbose_name="الشارع")
    city = models.CharField(max_length=255, verbose_name="المدينة")
    zip_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="الرمز البريدي")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط العرض")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط الطول")
    class Meta:
        verbose_name = "عنوان"
        verbose_name_plural = "العناوين"
    def __str__(self):
        return f"{self.street}, {self.city}"

class Cart(models.Model):
    # استخدام UUID بدلاً من ID عادي للتوليد التلقائي لرمز فريد لكل سلة
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "سلة تسوق"
        verbose_name_plural = "سلات التسوق"

    def __str__(self):
        return str(self.id)


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="السلة"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        verbose_name="المنتج"
    )
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="الكمية"
    )

    class Meta:
        verbose_name = "عنصر سلة"
        verbose_name_plural = "عناصر السلات"
        # منع تكرار نفس المنتج مرتين في نفس السلة
        unique_together = [['cart', 'product']]

class Order(models.Model):
    # 1. حالة الدفع (Payment Status)
    class PaymentStatus(models.TextChoices):
        PENDING = 'P', 'قيد الانتظار'
        COMPLETE = 'C', 'مكتمل'
        FAILED = 'F', 'فشل الدفع'

    # 2. حالة تنفيذ الطلب والشحن (Order Status)
    class OrderStatus(models.TextChoices):
        PENDING = 'P', 'قيد التجهيز'
        SHIPPED = 'S', 'تم الشحن'
        DELIVERED = 'D', 'تم التوصيل'
        CANCELED = 'C', 'ملغى'

    placed_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    
    payment_status = models.CharField(
        max_length=1,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="حالة الدفع"
    )
    
    order_status = models.CharField(
        max_length=1,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name="حالة الطلب"
    )

    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT, 
        related_name='orders',
        verbose_name="العميل"
    )

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    def __str__(self):
        return f"الطلب رقم #{self.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, 
        on_delete=models.PROTECT, 
        related_name='items',
        verbose_name="الطلب"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT, 
        related_name='order_items',
        verbose_name="المنتج"
    )
    quantity = models.PositiveSmallIntegerField(verbose_name="الكمية")
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="السعر عند الشراء"
    )

    class Meta:
        verbose_name = "عنصر طلب"
        verbose_name_plural = "عناصر الطلبات"
    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Review(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="المنتج"
    )
    name = models.CharField(max_length=255, verbose_name="اسم المقيم")
    description = models.TextField(verbose_name="التعليق")
    date = models.DateField(auto_now_add=True, verbose_name="التاريخ")

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
