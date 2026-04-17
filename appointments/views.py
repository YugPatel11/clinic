import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime
from .models import Patient, Appointment, FeeSettings

@login_required(login_url='login') 
def dashboard(request):
    today = timezone.now().date()
    is_owner = request.user.is_staff or request.user.is_superuser
    
    # ==========================================
    # 1. HANDLE FORM SUBMISSIONS (POST REQUESTS)
    # ==========================================
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_appointment':
            name = request.POST.get('name').strip()
            phone = request.POST.get('phone').replace(" ", "").strip()
            appt_date_str = request.POST.get('date')
            time_slot = request.POST.get('time_slot')
            
            # New fields (no medicine — added later by doctor)
            dob_str = request.POST.get('dob', '').strip()
            email = request.POST.get('email', '').strip()
            location = request.POST.get('location', '').strip()
            height = request.POST.get('height', '').strip()
            weight = request.POST.get('weight', '').strip()
            symptoms = request.POST.get('symptoms', '').strip()
            
            appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()

            if Appointment.objects.filter(date=appt_date, time_slot=time_slot).exclude(status='Cancelled').exists():
                messages.error(request, f'Error: {time_slot} on {appt_date.strftime("%d %b")} is already booked!')
                return redirect('dashboard')

            patient = Patient.objects.filter(phone_number=phone, name__iexact=name).first()
            if patient:
                is_new = False
                if dob_str and not patient.date_of_birth:
                    patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                if email:
                    patient.email = email
                if location:
                    patient.location = location
                patient.save()
            else:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
                patient = Patient.objects.create(name=name, phone_number=phone, date_of_birth=dob, email=email, location=location)
                is_new = True

            fee_settings = FeeSettings.objects.first()
            if not fee_settings:
                fee_settings = FeeSettings.objects.create(new_patient_fee=200, old_patient_fee=100)
            
            fee = fee_settings.new_patient_fee if is_new else fee_settings.old_patient_fee

            Appointment.objects.create(
                patient=patient,
                is_new_patient=is_new,
                date=appt_date,
                time_slot=time_slot,
                fee_charged=fee,
                status='Pending',
                height_cm=float(height) if height else None,
                weight_kg=float(weight) if weight else None,
                symptoms=symptoms,
                medicine_given='',  # Will be filled by doctor later
            )
            messages.success(request, f'Success: Appointment booked for {name}!')
            return redirect('dashboard')
        
        elif action == 'update_status':
            appt_id = request.POST.get('appointment_id')
            new_status = request.POST.get('status')
            medicine = request.POST.get('medicine_given', '').strip()
            med_price = request.POST.get('medicine_price', '').strip()
            height = request.POST.get('modal_height', '').strip()
            weight = request.POST.get('modal_weight', '').strip()
            
            appt = get_object_or_404(Appointment, id=appt_id)
            appt.status = new_status
            if medicine:
                appt.medicine_given = medicine
            if med_price:
                appt.medicine_price = float(med_price)
            if height:
                appt.height_cm = float(height)
            if weight:
                appt.weight_kg = float(weight)
            appt.save()
            messages.success(request, f'Appointment marked as {new_status}.')
            return redirect('dashboard')

    # ==========================================
    # 2. GENERATE BOOKED SLOTS FOR FRONTEND JS
    # ==========================================
    active_appointments = Appointment.objects.exclude(status='Cancelled')
    booked_slots_dict = {}
    for a in active_appointments:
        d_str = str(a.date)
        if d_str not in booked_slots_dict:
            booked_slots_dict[d_str] = []
        booked_slots_dict[d_str].append(a.time_slot)
    
    booked_slots_json = json.dumps(booked_slots_dict)

    # ==========================================
    # 3. GENERAL DASHBOARD STATS
    # ==========================================
    todays_appointments = Appointment.objects.filter(date=today)
    total_today = todays_appointments.count()
    new_patients = todays_appointments.filter(is_new_patient=True).count()
    old_patients = todays_appointments.filter(is_new_patient=False).count()
    revenue_today = todays_appointments.filter(status='Completed').aggregate(
        total=Sum('fee_charged') + Sum('medicine_price', default=0)
    )['total'] or 0

    # ==========================================
    # 4. CHART DATA — Dynamic range
    # ==========================================
    chart_range = request.GET.get('chart_range', '7days')
    chart_start_str = request.GET.get('chart_start', '')
    chart_end_str = request.GET.get('chart_end', '')
    
    if chart_range == 'custom' and chart_start_str and chart_end_str:
        chart_start = datetime.strptime(chart_start_str, '%Y-%m-%d').date()
        chart_end = datetime.strptime(chart_end_str, '%Y-%m-%d').date()
    elif chart_range == '30days':
        chart_end = today
        chart_start = today - timedelta(days=29)
    elif chart_range == 'this_week':
        chart_start = today - timedelta(days=today.weekday())
        chart_end = chart_start + timedelta(days=6)
    elif chart_range == 'this_month':
        chart_start = today.replace(day=1)
        # last day of month
        next_month = chart_start.replace(day=28) + timedelta(days=4)
        chart_end = next_month - timedelta(days=next_month.day)
    elif chart_range == 'last_month':
        first_this = today.replace(day=1)
        chart_end = first_this - timedelta(days=1)
        chart_start = chart_end.replace(day=1)
    else:  # default 7days
        chart_end = today
        chart_start = today - timedelta(days=6)
    
    chart_labels = []
    chart_patient_counts = []
    chart_revenue_data = []
    chart_new_patients = []
    chart_old_patients = []
    
    num_days = (chart_end - chart_start).days + 1
    for i in range(num_days):
        day = chart_start + timedelta(days=i)
        chart_labels.append(day.strftime('%d %b'))
        
        day_appts = Appointment.objects.filter(date=day)
        chart_patient_counts.append(day_appts.count())
        chart_new_patients.append(day_appts.filter(is_new_patient=True).count())
        chart_old_patients.append(day_appts.filter(is_new_patient=False).count())
        
        day_revenue_data = day_appts.filter(status='Completed').aggregate(
            fee=Sum('fee_charged'),
            med=Sum('medicine_price', default=0)
        )
        day_revenue = (day_revenue_data['fee'] or 0) + (day_revenue_data['med'] or 0)
        chart_revenue_data.append(float(day_revenue))
    
    total_patients_all = Patient.objects.count()

    # ==========================================
    # 5. ADVANCED SCHEDULE FILTERING + SEARCH
    # ==========================================
    display_date_str = request.GET.get('display_date', str(today))
    if not display_date_str:
        display_date_str = str(today)
        
    display_date = datetime.strptime(display_date_str, '%Y-%m-%d').date()
    schedule_filter = request.GET.get('schedule_filter', 'day')
    patient_search_query = request.GET.get('patient_q', '').strip()

    if schedule_filter == 'day':
        appointments_list = Appointment.objects.filter(date=display_date).order_by('time_slot')
        schedule_title = f"Schedule for {display_date.strftime('%d %b, %Y')}"
    elif schedule_filter == 'week':
        start_week = display_date - timedelta(days=display_date.weekday())
        end_week = start_week + timedelta(days=6)
        appointments_list = Appointment.objects.filter(date__range=[start_week, end_week]).order_by('date', 'time_slot')
        schedule_title = f"Week of {start_week.strftime('%d %b')}"
    elif schedule_filter == 'month':
        appointments_list = Appointment.objects.filter(date__year=display_date.year, date__month=display_date.month).order_by('date', 'time_slot')
        schedule_title = f"{display_date.strftime('%B %Y')} Schedule"
    elif schedule_filter == 'lifetime':
        appointments_list = Appointment.objects.all().order_by('-date', 'time_slot')
        schedule_title = "Lifetime Schedule"
    else:
        appointments_list = Appointment.objects.filter(date=display_date).order_by('time_slot')
        schedule_title = f"Schedule for {display_date.strftime('%d %b, %Y')}"
    
    # Apply patient name search filter
    if patient_search_query:
        appointments_list = appointments_list.filter(
            Q(patient__name__icontains=patient_search_query) | 
            Q(patient__phone_number__icontains=patient_search_query)
        )
        schedule_title = f"Search: \"{patient_search_query}\""

    # ==========================================
    # 6. OWNER ONLY: ADVANCED REVENUE BREAKDOWN
    # ==========================================
    admin_revenue = 0
    admin_revenue_new = 0
    admin_revenue_old = 0
    
    filter_type = request.GET.get('filter', 'weekly')
    patient_type = request.GET.get('patient_type', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if is_owner:
        completed_appts = Appointment.objects.filter(status='Completed')
        
        if filter_type == 'today':
            filtered_appts = completed_appts.filter(date=today)
        elif filter_type == 'weekly':
            start_week = today - timedelta(days=today.weekday())
            filtered_appts = completed_appts.filter(date__gte=start_week)
        elif filter_type == 'monthly':
            filtered_appts = completed_appts.filter(date__year=today.year, date__month=today.month)
        elif filter_type == 'custom' and start_date and end_date:
            filtered_appts = completed_appts.filter(date__range=[start_date, end_date])
        else:
            filtered_appts = completed_appts.filter(date=today)

        admin_revenue_new_data = filtered_appts.filter(is_new_patient=True).aggregate(
            fee=Sum('fee_charged'),
            med=Sum('medicine_price', default=0)
        )
        admin_revenue_new = (admin_revenue_new_data['fee'] or 0) + (admin_revenue_new_data['med'] or 0)

        admin_revenue_old_data = filtered_appts.filter(is_new_patient=False).aggregate(
            fee=Sum('fee_charged'),
            med=Sum('medicine_price', default=0)
        )
        admin_revenue_old = (admin_revenue_old_data['fee'] or 0) + (admin_revenue_old_data['med'] or 0)

        if patient_type == 'new':
            filtered_appts = filtered_appts.filter(is_new_patient=True)
        elif patient_type == 'old':
            filtered_appts = filtered_appts.filter(is_new_patient=False)

        admin_revenue_total_data = filtered_appts.aggregate(
            fee=Sum('fee_charged'),
            med=Sum('medicine_price', default=0)
        )
        admin_revenue = (admin_revenue_total_data['fee'] or 0) + (admin_revenue_total_data['med'] or 0)

    context = {
        'total_today': total_today,
        'new_patients': new_patients,
        'old_patients': old_patients,
        'revenue_today': revenue_today,
        'total_patients_all': total_patients_all,
        
        'appointments': appointments_list,
        'display_date': display_date_str,
        'schedule_filter': schedule_filter,
        'schedule_title': schedule_title,
        'booked_slots_json': booked_slots_json,
        'patient_search_query': patient_search_query,
        
        # Chart data
        'chart_labels_json': json.dumps(chart_labels),
        'chart_patient_counts_json': json.dumps(chart_patient_counts),
        'chart_revenue_json': json.dumps(chart_revenue_data),
        'chart_new_patients_json': json.dumps(chart_new_patients),
        'chart_old_patients_json': json.dumps(chart_old_patients),
        'chart_range': chart_range,
        'chart_start': chart_start_str or str(chart_start) if chart_range == 'custom' else '',
        'chart_end': chart_end_str or str(chart_end) if chart_range == 'custom' else '',
        
        'is_owner': is_owner,
        'filter_type': filter_type,
        'patient_type': patient_type,
        'start_date': start_date,
        'end_date': end_date,
        'admin_revenue': admin_revenue,
        'admin_revenue_new': admin_revenue_new,
        'admin_revenue_old': admin_revenue_old,
        'recent_histories': Appointment.objects.filter(status='Completed').select_related('patient').order_by('-date', '-id')[:5],
    }
    
    return render(request, 'appointments/dashboard.html', context)


@login_required(login_url='login')
def patient_search(request):
    query = request.GET.get('q', '').strip()
    patients = []
    
    if query:
        patients = Patient.objects.filter(
            Q(name__icontains=query) | Q(phone_number__icontains=query)
        ).annotate(
            appointment_count=Count('appointments')
        ).order_by('-created_at')
    
    context = {
        'query': query,
        'patients': patients,
    }
    return render(request, 'appointments/patient_search.html', context)


@login_required(login_url='login')
def patient_history(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    appointments = Appointment.objects.filter(patient=patient).order_by('-date', '-time_slot')
    
    total_visits = appointments.count()
    total_spent_data = appointments.filter(status='Completed').aggregate(
        fee=Sum('fee_charged'),
        med=Sum('medicine_price', default=0)
    )
    total_spent = (total_spent_data['fee'] or 0) + (total_spent_data['med'] or 0)
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'total_visits': total_visits,
        'total_spent': total_spent,
    }
    return render(request, 'appointments/patient_history.html', context)