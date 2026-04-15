from django.db import models
from django.utils import timezone

class Patient(models.Model):
    name = models.CharField(max_length=100)
    # Phone number and name combination identifies Old vs New patients
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=150, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

class FeeSettings(models.Model):
    # Store fees in the database so admin can change them anytime
    new_patient_fee = models.DecimalField(max_digits=8, decimal_places=2, default=200.00)
    old_patient_fee = models.DecimalField(max_digits=8, decimal_places=2, default=100.00)

    class Meta:
        verbose_name_plural = "Fee Settings"

    def __str__(self):
        return f"Fees - New: ₹{self.new_patient_fee} | Old: ₹{self.old_patient_fee}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    TIME_SLOTS = [
        ('09:00 AM', '09:00 AM'), ('09:30 AM', '09:30 AM'),
        ('10:00 AM', '10:00 AM'), ('10:30 AM', '10:30 AM'),
        ('11:00 AM', '11:00 AM'), ('11:30 AM', '11:30 AM'),
        ('12:00 PM', '12:00 PM'), ('12:30 PM', '12:30 PM'),
        ('02:00 PM', '02:00 PM'), ('02:30 PM', '02:30 PM'),
        ('03:00 PM', '03:00 PM'), ('03:30 PM', '03:30 PM'),
        ('04:00 PM', '04:00 PM'), ('04:30 PM', '04:30 PM'),
        ('05:00 PM', '05:00 PM'), ('05:30 PM', '05:30 PM'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    is_new_patient = models.BooleanField(default=True)
    date = models.DateField(default=timezone.now)
    time_slot = models.CharField(max_length=10, choices=TIME_SLOTS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    fee_charged = models.DecimalField(max_digits=8, decimal_places=2)

    # New clinical fields
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="Height in cm")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="Weight in kg")
    symptoms = models.TextField(blank=True, default='', help_text="Problem / Symptoms described by patient")
    medicine_given = models.TextField(blank=True, default='', help_text="Medicine prescribed or given")
    medicine_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This prevents double booking at the database level for the same day and time
        unique_together = ('date', 'time_slot')

    def __str__(self):
        return f"{self.patient.name} - {self.date} at {self.time_slot}"

class Subscription(models.Model):
    # Your Kill-Switch for clients who don't pay the monthly fee
    is_active = models.BooleanField(
        default=True, 
        help_text="Uncheck this to lock the client out of the system."
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Client Subscription Status"

    def __str__(self):
        return "Website is ACTIVE" if self.is_active else "Website is SUSPENDED"