from django.shortcuts import render
from .models import Subscription

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. ALWAYS let the Super Admin (You) through, no matter what!
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)

        # 2. ALWAYS allow access to the admin panel URL so you can log in
        if request.path.startswith('/admin/'):
            return self.get_response(request)
            
        # 3. For everyone else (Owner & Receptionist), check if the bill is paid
        subscription = Subscription.objects.first()
        if subscription and not subscription.is_active:
            # If not active, block them and show the suspended page
            return render(request, 'appointments/suspended.html')

        # If active, let them through
        return self.get_response(request)