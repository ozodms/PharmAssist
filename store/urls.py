from django.urls import path
from . import views

urlpatterns = [

	path('', views.store, name="store"),
	path('cart/', views.cart, name="cart"),
	path('checkout/', views.checkout, name="checkout"),
    path('order/', views.order_confirm, name="order"),
    path('order_item/', views.order_item, name="order_item")

]
