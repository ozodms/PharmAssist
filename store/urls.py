from django.urls import path
from . import views

urlpatterns = [

	path('', views.store, name="store"),
	path('cart/', views.cart, name="cart"),
	path('checkout/', views.checkout, name="checkout"),
    path('order/', views.order_confirm, name="order"),
    path('product/<int:pk>/', views.order_item, name='order_item'),
    path('update_item/', views.updateItem, name="update_item"),
    path('set_qty/<int:pk>/', views.set_quantity, name='set_qty'),
    path('login/', views.login_views, name='login'),
    path('register/', views.register_views, name='register'),
    path('logout/', views.logout_views, name='logout'),
    path('profile/', views.profile_views, name='profile'),
]
