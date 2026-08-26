from django.shortcuts import render
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter ,OrderingFilter
from rest_framework.viewsets import ModelViewSet ,  GenericViewSet
from rest_framework import mixins
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAdminUser , IsAuthenticated
from rest_framework.response import Response  
from rest_framework.decorators import action
from api.models import Category , Product , Cart , CartItem , Order , OrderItem ,Address , Customer 
from api.serializers import CategorySerializer , SimpleProductSerializer , CartItemSerializer , CartSerializer , AddCartItemSerializer , UpdateCartItemSerializer , CreateOrderSerializer , UpdateOrderSerializer , OrderSerializer ,OrderItemSerializer,AddressSerializer ,CustomerSerializer


class CustomerViewSet(ModelViewSet):
    # جلب جميع بيانات العملاء مسبقاً مع عناوينهم المربوطة لتقليل استعلامات قاعدة البيانات (Optimization)
    queryset = Customer.objects.prefetch_related('addresses').all()
    
    # تحديد الـ Serializer المسؤول عن تحويل البيانات بين JSON وموديل العميل
    serializer_class = CustomerSerializer
    
    # اشتراط تسجيل الدخول (وجود Access Token) للوصول إلى هذا الـ ViewSet
    permission_classes = [IsAuthenticated]

    # إنشاء Endpoint مخصص باسم '/me' على مستوى الـ ViewSet ككل (detail=False) يدعم عمليات القراءة والتحديث
    @action(detail=False, methods=['GET', 'PUT', 'PATCH'])
    def me(self, request):
        # البحث عن كائن العميل المرتبط بالمسجل حالياً، وإن لم يكن موجوداً يتم إنشاؤه تلقائياً
        customer, created = Customer.objects.get_or_create(user_id=request.user.id)
        
        # في حال كان نوع الطلب GET (استعراض الملف الشخصي)
        if request.method == 'GET':
            # تحويل بيانات العميل إلى صيغة Serializer
            serializer = CustomerSerializer(customer)
            # إرجاع البيانات في الـ Response بصيغة JSON
            return Response(serializer.data)
            
        # في حال كان نوع الطلب PUT (تحديث كامل) أو PATCH (تحديث جزئي)
        elif request.method in ['PUT', 'PATCH']:
            # تمرير البيانات الجديدة للـ Serializer، وتفعيل التحديث الجزئي عند استخدام PATCH
            serializer = CustomerSerializer(customer, data=request.data, partial=(request.method == 'PATCH'))
            # التحقق من صحة البيانات المدخلة قبل الحفظ وإرجاع استثناء 400 في حال وجود خطأ
            serializer.is_valid(raise_exception=True)
            # حفظ التغيرات الجديدة في قاعدة البيانات
            serializer.save()
            # إرجاع البيانات المحدثة للعميل داخل الـ Response
            return Response(serializer.data)

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.annotate(product_count=Count('products'))
    serializer_class = CategorySerializer

class ProductViewSet(ModelViewSet):
    # تم تعديل السطر لجلب المنتجات والتصنيفات مباشرة بدون prefetch_related
    queryset = Product.objects.select_related('category').all().order_by('id')
    serializer_class = SimpleProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category_id']
    search_fields = ['title', 'description']  
    ordering_fields = ['unit_price', 'title'] 

class CartViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer

class CartItemViewSet(ModelViewSet):
    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs['cart_pk']).select_related('product')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method in ['PUT', 'PATCH']:
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['cart_id'] = self.kwargs['cart_pk']
        return context

class OrderViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options'] 
    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data, context={'user_id': self.request.user.id})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        elif self.request.method in ['PUT', 'PATCH']:
            return UpdateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.prefetch_related('items__product').all()

        return Order.objects.filter(customer__user_id=user.id).prefetch_related('items__product')

# views.py
class AddressViewSet(ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(customer__user_id=self.request.user.id)

    def get_serializer_context(self):
        return {'user_id': self.request.user.id}

