from django.urls import path, include
from rest_framework_nested import routers
from api import views
#الاساسي
router = routers.DefaultRouter()
router.register('categories', views.CategoryViewSet, basename='categories')
router.register('products', views.ProductViewSet, basename='products')
router.register('carts', views.CartViewSet, basename='carts')
router.register('orders', views.OrderViewSet, basename='orders')
router.register('addresses', views.AddressViewSet, basename='addresses')
router.register('customers', views.CustomerViewSet, basename='customers')


#متداخل 
carts_router = routers.NestedDefaultRouter(router, 'carts', lookup='cart')
carts_router.register('items', views.CartItemViewSet, basename='cart-items')


urlpatterns = [
    path('', include(router.urls)),
    path('', include(carts_router.urls)),
    path('stripe/webhook/', views.stripe_webhook, name='stripe-webhook'),
]