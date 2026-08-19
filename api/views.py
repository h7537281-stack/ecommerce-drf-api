from django.shortcuts import render
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter ,OrderingFilter
from rest_framework.viewsets import ModelViewSet ,  GenericViewSet
from rest_framework import mixins
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAdminUser , IsAuthenticated
from rest_framework.response import Response  
from api.models import Category , Product , Cart , CartItem , Order , OrderItem
from api.serializers import CategorySerializer , SimpleProductSerializer , CartItemSerializer , CartSerializer , AddCartItemSerializer , UpdateCartItemSerializer , CreateOrderSerializer , UpdateOrderSerializer , OrderSerializer ,OrderItemSerializer


class CategoryViewSet(ModelViewSet):
    queryset=Category.objects.annotate(product_count=Count('products')).all() #count the products in each category
    serializer_class=CategorySerializer

class ProductViewSet(ModelViewSet):
    queryset=Product.objects.prefetch_related('images').all().order_by('id')#to get all images in one request for N+1 problem
    serializer_class=SimpleProductSerializer
    filter_backends=[DjangoFilterBackend,SearchFilter,OrderingFilter]#set the filters tools we gonna use
    filterset_fields=['category_id']# products/?category_id=2/
    Search_fields=['title','description']#products/?title=فيتامين
    Ordering_fields=['unit_price','last_update']#products/?ordering=-unit_price/

class CartViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin , mixins.DestroyModelMixin, GenericViewSet):
    queryset=Cart.objects.prefetch_related('items__product').all()
    serializer_class=CartSerializer

class CartItemViewSet(ModelViewSet):
    def get_queryset(self):#the kwargs store the values that came from the url (card_pk)
        return CartItem.objects.filter(cart_id=self.kwargs['cart_pk']).select_related('product')
    
    def get_serializer_class(self):
        if self.request.method =='POST':
            return AddCartItemSerializer
        elif self.request.method in ['PUT','PATCH']:
            return UpdateCartItemSerializer
        return CartItemSerializer
    def get_serializer_context(self):#override of the real fun to not having the  cart id shown 
        context=super().get_serializer_context()
        context['cart_id'] = self.kwargs['cart_pk']
        return context

class OrderViewSet(ModelViewSet):
    http_method_names=['get','post','delete','head','options']
    def get_permissions(self):
        if self.request.method in ['PATCH','DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    def create(self, request, *args, **kwargs):
        serializer=CreateOrderSerializer(data=request.data, context={'user_id':self.request.user.id} )
        serializer.is_valid(raise_exception=True)
        order=serializer.save()
        serializer=OrderSerializer(order)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        if self.request.method=='POST':
            return CreateOrderSerializer
        elif self.request.method in ['PUT','PATCH']:
            return UpdateOrderSerializer
        return OrderSerializer
    def get_queryset(self):
      user = self.request.user
      if user.is_staff:
        return Order.objects.prefetch_related('items__product').all()
    
       # ✅ الفلترة عبر علاقة customer بدلاً من user المباشرة
      return Order.objects.filter(customer__user_id=user.id).prefetch_related('items__product')

        