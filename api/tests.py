from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from api.models import Cart
User = get_user_model()
class OrderAPITestCase(APITestCase):
    def setUp(self):
        """تجهيز البيئة الافتراضية قبل تشغيل أي اختبار"""
        # 1. إنشاء مستخدم تجريبي وتوثيق الهوية بضغطة واحدة
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.force_authenticate(user=self.user)
        
        # 2. إنشاء سلة فارغة لاختبارها
        self.cart = Cart.objects.create()

    def test_create_order_with_empty_cart_fails(self):
        """اختبار: التأكد من رفض تقديم طلب إذا كانت السلة فارغة"""
        response = self.client.post('/api/orders/', {'cart_id': self.cart.id})
        
        # نتحقق أن الاستجابة هي 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)