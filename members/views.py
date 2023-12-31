from django.shortcuts import render
from django.shortcuts import redirect, render
from django.views.generic import CreateView
from .models import *
from .forms import *
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .decorators import *
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render, get_object_or_404



def login(request):
    form = LoginForm
    context = {
        'form': form
    }
    return render(request, 'login.html', context)


class LoginView(auth_views.LoginView):
    form_class = LoginForm
    template_name = 'login.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_member:
                return reverse('member_dashboard')
            elif user.is_management:
                return reverse('management_dashboard')
            elif user.is_vendor:
                return reverse('vendor_dashboard')
            
        else:
            return reverse('login')
        


class RegisterMemberView(CreateView):
    model = User
    form_class = MemberSignUpForm
    template_name = 'member/register.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'member'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        #login(self.request, user)
        return redirect('login')
  
    
class RegisterManagementView(CreateView):
    model = User
    form_class = ManagementSignUpForm
    template_name = 'management/register.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'management'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        #login(self.request, user)
        return redirect('login')
    
@login_required
@member_required
def MemberDashboard(request):
    #loans =  Loan.objects.filter(group_member_id=request.user.member)
    context = {
        'loans': 0
    }
    return render(request, 'member/dashboard.html', context)

@login_required
@management_required
def ManagementDashboard(request):
    context = {
        'loans': 0
    }
    return render(request, 'management/dashboard.html', context)



def update_commissions():
    current_month = datetime.date.today().month
    sales_for_current_month = Sale.objects.filter(date_paid__month=current_month)
    
    allowances = {
        (0, 19000): 0,
        (20000, 100000): 1500,
        (101000, 200000): 4000,
        (201000, 250000): 10000,
        (251000, 550000): 12000,
        (551000, 850000): 15000,
    }

    for sale in sales_for_current_month:
        total_amount_paid = sale.loan_amount_paid
        allowance = 0

        for amount_range, allowance_value in allowances.items():
            if amount_range[0] <= total_amount_paid <= amount_range[1]:
                allowance = allowance_value

        commission = (total_amount_paid * Decimal('0.05')) + Decimal(allowance)
        sale.commission = commission
        sale.save()
        
@login_required
def home(request):
    # Call the update_commissions function to update commissions first
    update_commissions()

    # Retrieve the logged-in user's commission for the current month
    current_user = request.user
    current_month = datetime.date.today().month
    user_commission = Sale.objects.filter(agent=current_user, date_paid__month=current_month).aggregate(total=Sum('commission'))['total'] or 0

    # Count the total number of clients for the current user
    total_clients = Client.objects.filter(user=current_user).count()

    # Retrieve the routes for the currently logged-in user
    user_routes = RoutePlan.objects.filter(user=current_user)

    return render(request, 'users/home.html', {
        'commission': user_commission,
        'total_clients': total_clients,
        'user_routes': user_routes  # Pass the user's routes to the template
    })
    
# @login_required
# @permission_required('your_app.add_sale', raise_exception=True)
def add_sale(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sales')
    else:
        form = SaleForm()
    return render(request, 'users/add_sale.html', {'form': form})

def display_sales(request):
    sales = Sale.objects.all()
    return render(request, 'users/display_sales.html', {'sales': sales})

def monthly_sales(request):
    monthly_totals = Sale.objects.annotate(
        month=TruncMonth('date_paid')
    ).values('month').annotate(total_amount_paid=Sum('loan_amount_paid')).order_by('month')

    return render(request, 'users/monthly_sales.html', {'monthly_totals': monthly_totals})



@login_required
def monthly_sales(request):
    current_user = request.user  # Get the currently logged-in user

    monthly_totals = Sale.objects.filter(agent=current_user).annotate(
        month=TruncMonth('date_paid')
    ).values('month').annotate(total_amount_paid=Sum('loan_amount_paid')).order_by('month')

    # Define allowances for different ranges of total amount paid
    allowances = {
        (0, 19000): 0,
        (20000, 100000): 1500,
        (101000, 200000): 4000,
        (201000, 250000): 10000,
        (251000, 550000): 12000,
        (551000, 850000): 15000,
    }

    # Calculate and update the commission for each sale
    for entry in monthly_totals:
        total_amount_paid = entry['total_amount_paid']
        for amount_range, allowance in allowances.items():
            if amount_range[0] <= total_amount_paid <= amount_range[1]:
                commission = (total_amount_paid * Decimal('0.05')) + Decimal(allowance)
                entry['commission'] = commission

    return render(request, 'users/monthly_sales.html', {'monthly_totals': monthly_totals})

# @login_required
def managementView(request):
    return render(request, 'users/management.html')

@login_required
def add_client(request):
    total_clients = Client.objects.count()  # Get the count of clients
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.user = request.user
            client.save()
            return redirect('success_page')
        
    else:
        form = ClientForm()

    return render(request, 'users/add_client.html', {'form': form, 'total_clients': total_clients})


def calendar_view(request):
    # Create a calendar object
    cal = calendar.HTMLCalendar(calendar.SUNDAY)

    # Generate the HTML for the current month's calendar
    html_calendar = cal.formatmonth(2023, 10)

    # You can customize the year and month as needed
    # Replace 2023 and 10 with the desired year and month values

    return render(request, 'users/record_attendance.html', {'calendar': html_calendar})

@login_required
def record_attendance(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            user = request.user
            date = datetime.date.today()
            latitude = form.cleaned_data['latitude']
            longitude = form.cleaned_data['longitude']
            timestamp = datetime.datetime.now()

            try:
                Attendance.objects.create(user=user, date=date, location=f"({latitude}, {longitude})", latitude=latitude, longitude=longitude, timestamp=timestamp)
                # Display a JavaScript alert
                return render(request, 'users/record_attendance.html', {'form': form, 'success_message': 'Attendance recorded successfully!'})
            except Exception as e:
                error_message = f"Error occurred: {str(e)}"
                return render(request, 'users/record_attendance.html', {'form': form, 'error_message': error_message})
    else:
        form = AttendanceForm()

    return render(request, 'users/record_attendance.html', {'form': form})

def success_view(request):
    return render(request, 'users/success.html')

@login_required
def user_clients(request):
    # Display clients added by the currently logged-in user
    clients = Client.objects.filter(user=request.user)
    return render(request, 'users/user_clients.html', {'clients': clients})

def client_details(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, 'users/client_details.html', {'client': client})

def attendance_success(request):
    return render(request, 'attendance_success.html')

def charts(request):
    return render(request, 'users/chats.html')

def commission_page(request):
    # Retrieve the agent's commission and sales data
    agent = request.user
    commission = Commission.objects.get(agent=agent)
    sales = Sale.objects.filter(agent=agent)

    return render(request, 'users/commission_page.html', {'commission': commission, 'sales': sales})

def create_route_plan(request):
    if request.method == 'POST':
        form = RoutePlanForm(request.POST)
        if form.is_valid():
            form.instance.user = request.user  # Assign the current user to the route plan
            form.save()
            return redirect('create_route_plan')  # Redirect to a page displaying route plans
    else:
        form = RoutePlanForm()

    return render(request, 'users/create_route_plan.html', {'form': form})