from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # The main dashboard page
    path('', views.dashboard, name='dashboard'),
    
    # Patient search and history
    path('search/', views.patient_search, name='patient_search'),
    path('patient/<int:patient_id>/history/', views.patient_history, name='patient_history'),
    
    # Custom Login and Logout pages built into Django
    path('login/', auth_views.LoginView.as_view(
        template_name='appointments/login.html', 
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]