from django.contrib import admin
from .models import Patient, FeeSettings, Appointment, Subscription

# This customizes how Patients look in the admin panel
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'date_of_birth', 'created_at')
    search_fields = ('name', 'phone_number')

# This customizes how Appointments look in the admin panel
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date', 'time_slot', 'status', 'fee_charged', 'symptoms_short', 'medicine_given_short')
    list_filter = ('status', 'date', 'is_new_patient')
    search_fields = ('patient__name', 'patient__phone_number', 'symptoms', 'medicine_given')

    @admin.display(description='Symptoms')
    def symptoms_short(self, obj):
        return obj.symptoms[:50] + '...' if len(obj.symptoms) > 50 else obj.symptoms

    @admin.display(description='Medicine')
    def medicine_given_short(self, obj):
        return obj.medicine_given[:50] + '...' if len(obj.medicine_given) > 50 else obj.medicine_given

# This shows the Fee settings
@admin.register(FeeSettings)
class FeeSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'new_patient_fee', 'old_patient_fee')

# This is your Kill Switch!
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'last_updated')