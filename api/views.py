from django.shortcuts import render
import stripe
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter ,OrderingFilter
from rest_framework.viewsets import ModelViewSet ,  GenericViewSet
from rest_framework import mixins
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAdminUser , AllowAny,  IsAuthenticated
from rest_framework.response import Response  
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from .tasks import send_order_confirmation_email
from api.models import Category , Product , Cart , CartItem , Order , OrderItem ,Address , Customer 
from api.serializers import CategorySerializer , SimpleProductSerializer , CartItemSerializer , CartSerializer , AddCartItemSerializer , UpdateCartItemSerializer , CreateOrderSerializer , UpdateOrderSerializer , OrderSerializer ,OrderItemSerializer,AddressSerializer ,CustomerSerializer
stripe.api_key = settings.STRIPE_SECRET_KEY

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')

        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        # إنشاء المستخدم الجديد
        user = User.objects.create_user(username=username, password=password, email=email)
        
        # توليد التوكن مباشرة ليتم تسجيل دخوله بعد التسجيل
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'User registered successfully',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist() # وضع التوكن في القائمة السوداء
            return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
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

    def get_permissions(self):
        # إذا كان الطلب قراءة (GET, HEAD, OPTIONS)، اسمح به لأي شخص
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [AllowAny()]
        # غير ذلك (POST, PUT, DELETE)، اشترط أن يكون المستخدم أدمن
        return [IsAdminUser()]
    
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.select_related('category').all().order_by('id')
    serializer_class = SimpleProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category_id']
    search_fields = ['title', 'description']  
    ordering_fields = ['unit_price'] 

    # تحديد الصلاحيات بناءً على الـ Action داخل الكلاس نفسه
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # التصفح والعرض متاح للجميع (Read-only)
            return [AllowAny()]
        # الإضافة والتعديل والحذف متاحة للآدمن فقط
        return [IsAdminUser()]

    @method_decorator(cache_page(60 * 15))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
        if self.action == 'confirm_payment':
            return [AllowAny()]
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
        # في حال كان الأكشن confirm_payment، اسمح بالبحث في كافة الطلبات
        if self.action == 'confirm_payment':
            return Order.objects.all()

        user = self.request.user
        if user.is_staff:
            return Order.objects.prefetch_related('items__product').all()

        return Order.objects.filter(customer__user_id=user.id).prefetch_related('items__product')
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def pay(self, request, pk=None):
        """
        إنشاء جلسة دفع عبر Stripe وإعادة رابط الدفع للعميل
        المسار: POST /api/orders/{id}/pay/
        """
        # جلب كائن الطلب المحدد من قاعدة البيانات بناءً على الـ ID في المسار
        order = self.get_object()
        
        # التحقق مما إذا كان الطلب مدفوعاً مسبقاً لمنع تكرار الدفع
        if order.payment_status == 'C':  # 'C' تعني Complete (مكتمل)
            return Response(
                {'detail': 'هذا الطلب مدفوع بالفعل!'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # تجهيز مصفوفة المنتجات (line_items) بالتنسيق المطلوب لدى Stripe
        line_items = []
        
        # المرور على كل عنصر من عناصر الطلب الحالي
        for item in order.items.all():
            line_items.append({
                'price_data': {
                    'currency': 'usd',  # تحديد العملة المستخدمة في عملية الدفع
                    'product_data': {
                        'name': item.product.title,  # اسم المنتج الذي يظهر في صفحة الدفع
                    },
                    # تحويل السعر إلى أصغر وحدة عملة (المبلغ * 100 لأن Stripe يتعامل بالسينت)
                    'unit_amount': int(item.unit_price * 100), 
                },
                'quantity': item.quantity,  # الكمية المطلوبة من المنتج
            })

        try:
            # إنشاء جلسة دفع جديدة لدى خوادم Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],  # تحديد وسيلة الدفع (بطاقة ائتمان)
                line_items=line_items,          # قائمة المنتجات والأسعار
                mode='payment',                 # نوع الجلسة (عملية دفع مباشرة لمرة واحدة)
                metadata={'order_id': order.id},  # إرسال رقم الطلب مع الجلسة ليتعرف عليه الـ Webhook لاحقاً
                # رابط العودة عند نجاح عملية الدفع (يوجّه للـ endpoint الذي يؤكد العملية)
                success_url=f'http://localhost:8000/api/orders/{order.id}/confirm_payment/',
                
                # رابط العودة عند إلغاء أو عدم إتمام عملية الدفع
                cancel_url='http://localhost:8000/api/orders/canceled/',
            )
            
            # إرجاع رابط صفحة Stripe للعميل ليتمكن من زيارته وإكمال الدفع
            return Response({'checkout_url': checkout_session.url})

        except Exception as e:
            # معالجة أي خطأ قد يحدث أثناء التواصل مع خوادم Stripe
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # -------------------------------------------------------------
    # 2️⃣ أكشن تأكيد الدفع بعد عودة المستخدم من Stripe (Callback)
    # -------------------------------------------------------------
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def confirm_payment(self, request, pk=None):
        """
        صفحة العودة بعد نجاح الدفع (Success URL)
        """
        order = self.get_object()
        
        # لا تقومي بتغيير حالة الدفع هنا يدوياً، بل تحققي إن كان الـ Webhook قد قام بتحديثها، 
        # أو أعيدي رسالة تأكيد للعميل بأن طلبه تم استلامه بنجاح
        if order.payment_status == 'C':
            return Response({'message': f'شكراً لك! تم تأكيد دفع الطلب رقم #{order.id} بنجاح.'})
        
        return Response({'message': f'الطلب رقم #{id} جاري معالجة عملية الدفع الخاصة به.'})
@csrf_exempt
def stripe_webhook(request):
    # استقبال البيانات الخام (payload) المرسلة من سيرفر Stripe
    payload = request.body
    
    # جلب التوقيع الرقمي للتحقق من هوية المرسل وضمان أن الطلب لم يتم التلاعب به
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # جلب المفتاح السري الخاص بالـ Webhook المخزن في إعدادات المشروع
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        # التحقق من صحة التوقيع والبيانات عبر مكتبة Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        # إذا كان التوقيع غير صالح أو البيانات تالفة، يتم رفض الطلب بإرجاع 400
        return HttpResponse(status=400)

    # التحقق مما إذا كان الحدث المرسل يمثل اكتمال عملية الدفع بنجاح
    if event['type'] == 'checkout.session.completed':
        # استخراج كائن الجلسة من تفاصيل الحدث القادم
        session = event['data']['object']
        
        # استخراج رقم الطلب (order_id) الذي قمنا بتخزينه مسبقاً في الـ metadata
        order_id = session.get('metadata', {}).get('order_id')
        
        # استخراج إيميل الزبون الحقيقي المخزن في جلسة الدفع (أو من كائن customer_details)
        customer_email = session.get('customer_details', {}).get('email') or session.get('customer_email')

        if order_id:
            try:
                # جلب الطلب من قاعدة البيانات وتحديث حالة الدفع إلى مكتمل ('C')
                order = Order.objects.get(id=order_id)
                order.payment_status = 'C'
                order.save()

                # إرسال إيميل التأكيد للزبون في الخلفية عبر Celery إذا توفر الإيميل
                if customer_email:
                    send_order_confirmation_email.delay(order.id, customer_email)

            except Order.DoesNotExist:
                pass  # تجاهل الخطأ إذا لم يتم العثور على الطلب

    # إرجاع استجابة نجاح (200 OK) لإخبار Stripe بأن الـ Webhook تم استقباله ومعالجته بنجاح
    return HttpResponse(status=200)
class AddressViewSet(ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(customer__user_id=self.request.user.id)

    def get_serializer_context(self):
        return {'user_id': self.request.user.id}

