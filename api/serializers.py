from decimal import Decimal
from rest_framework import serializers
from .models import Product , Order ,OrderItem , Review , Cart , CartItem , Category , Address,Customer
from django.db import transaction
class CategorySerializer(serializers.ModelSerializer):
    product_count=serializers.IntegerField(read_only=True,default=0)#conts of products og a singel category 
    class Meta:
        model=Category
        fields=['id','title', 'slug','product_count']


class SimpleProductSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = Product
        fields = [
            'id', 
            'title', 
            'slug', 
            'description', 
            'inventory', 
            'unit_price', 
            'category', 
            'image', 
        ]

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model=Review
        fields=['id', 'name','description','date']
    def create(self, validated_data):
        product_id=self.context['product_id']
        return Review.objects.create(product_id=product_id, **validated_data)
#show (get) for one product 
class CartItemSerializer(serializers.ModelSerializer):
    product=SimpleProductSerializer()
    total_price=serializers.SerializerMethodField()#read  only 
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    def get_total_price(self, cart_item:CartItem):
        return cart_item.quantity * cart_item.product.unit_price
#add (create)
class AddCartItemSerializer(serializers.ModelSerializer):
    product_id=serializers.IntegerField()
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity']
#already faund function
    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
          raise serializers.ValidationError('لا يوجد منتج بهذا الرقم المعرف.')
        return value
    def save(self,**kwargs):
        cart_id=self.context['cart_id']
        product_id=self.validated_data['product_id']
        quantity=self.validated_data['quantity']
        try:
            cart_item=CartItem.objects.get(cart_id=cart_id, product_id=product_id)
            cart_item.quantity +=quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(cart_id=cart_id, **self.validated_data)
        return self.instance

class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity']
#all the cart product 
class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)  # Nested Serializer لعناصر السلة
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at']

    def get_total_price(self, cart: Cart):
        return sum([item.quantity * item.product.unit_price for item in cart.items.all()])

#the cart will be tansmitted to the order

class CreateOrderSerializer(serializers.Serializer):
    """سيريالايزر مخصص لإنشاء طلب جديد بناءً على رقم السلة"""
    cart_id = serializers.UUIDField()

    def validate_cart_id(self, cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise serializers.ValidationError('لا توجد سلة بهذا الرقم المعرف.')
        if CartItem.objects.filter(cart_id=cart_id).count() == 0:
            raise serializers.ValidationError('السلة فارغة، لا يمكنك تقديم طلب بصيدلية فارغة.')
        return cart_id

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            user_id = self.context['user_id']

            # ✅ 1. جلب أو إنشاء كائن Customer المرتبط بالـ user_id الحالي
            customer, _ = Customer.objects.get_or_create(user_id=user_id)

            # ✅ 2. إنشاء كائن الطلب وربطه بـ customer بدلاً من user_id المباشر
            order = Order.objects.create(customer=customer)

            # 3. تحويل عناصر السلة إلى عناصر طلب
            cart_items = CartItem.objects.select_related('product').filter(cart_id=cart_id)
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    unit_price=item.product.unit_price,
                    quantity=item.quantity
                )
                for item in cart_items
            ]
            OrderItem.objects.bulk_create(order_items)

            # 4. حذف السلة بعد تحويلها لطلب ناجح
            Cart.objects.filter(pk=cart_id).delete()

            return order


class UpdateOrderSerializer(serializers.ModelSerializer):
    """سيريالايزر لتعديل حالة الدفع للطلب (يستخدمه المشرفون)"""
    class Meta:
        model = Order
        fields = ['payment_status']


class OrderItemSerializer(serializers.ModelSerializer):
    """سيريالايزر لعرض عناصر الطلب مع بيانات المنتج السريعة"""
    product = SimpleProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'unit_price', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    """سيريالايزر لعرض تفاصيل الطلب الكاملة وقائمة المنتجات المشتراة"""
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        # ✅ استبدال 'user' بـ 'customer' لتتوافق مع حقول الموديل
        fields = ['id', 'customer', 'placed_at', 'payment_status', 'items']

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'street', 'city', 'zip_code', 'latitude', 'longitude']

    def create(self, validated_data):
        # ربط العنوان تلقائياً بالعميل المسجل حالياً
        user_id = self.context['user_id']
        customer = Customer.objects.get(user_id=user_id)
        return Address.objects.create(customer=customer, **validated_data)
    
class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    # عرض العناوين المربوطة بالعميل فقط لصلة الـ GET (Read-only)
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'user_id', 'phone', 'addresses']