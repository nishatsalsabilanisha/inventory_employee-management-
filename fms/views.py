from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_exempt
from .models import Customer, Product, Order, Cart
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User
from .models import (
    Employee,
    Product,
    Attendance,
    Customer,
    Order,
    PasswordResetToken,
    CancellationRequest,
)
from .models import EmployeeProfile, Production, PaymentTransaction, Leave, OfficeIP, SalaryPayment, Announcement
from .models import ProductColor, ProductSize, ProductTextile, ProductVariant, ProductImage
from .models import Department, JobPosition, InventoryLog
from .models import log_inventory
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .forms import (
    ProductForm,
    ProductionForm,
    BonusForm,
    AttendanceEditForm,
    CustomerRegisterForm,
    CustomerLoginForm,
    PasswordResetRequestForm,
    SetPasswordForm,
    OrderForm,
    LeaveForm,
    OfficeIPForm,
    DepartmentForm,
    JobPositionForm,
    EmployeeAssignmentForm,
    StockUpdateForm,
    validate_email_format,
    email_already_exists,
    validate_strong_password,
)
from django.db.models import Sum, Avg, Q, Count, F
from django.db import transaction
from django.db import IntegrityError
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
import calendar


# ============================================================
# PUBLIC PAGES
# ============================================================
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from django.template.loader import render_to_string
from io import BytesIO
from django.http import JsonResponse
import uuid
import secrets
import requests
import json
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404

# PDF generation library - imported lazily to avoid issues
pisa = None


# ============================================================
# ATTENDANCE HELPERS
# ============================================================
OFFICE_START_TIME = time(9, 0)  # Office start time: 09:00 AM
OFFICE_END_TIME = time(17, 0)  # Office end time: 05:00 PM


def attendance_window_error(now_time):
    """Return an error message if now_time is outside office hours, else None.

    Attendance is allowed only between 09:00 AM and 05:00 PM.
    """
    if now_time < OFFICE_START_TIME:
        return "Attendance is not available yet. Attendance starts at 09:00 AM."
    if now_time > OFFICE_END_TIME:
        return "Attendance time has ended for today. You can no longer mark attendance."
    return None


def get_client_ip(request):
    """Get the real IP address of the current request."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_office_ip(request):
    """Return True if the request comes from an allowed office IP."""
    ip = get_client_ip(request)
    return OfficeIP.objects.filter(ip_address=ip, is_active=True).exists()


def attendance_status_for(check_in_time):
    """Present if checked in at/before 09:00 AM, otherwise Late."""
    if check_in_time and check_in_time > OFFICE_START_TIME:
        return "Late"
    return "Present"


def format_working_hours(check_in_time, check_out_time):
    """Return working duration as 'Xh Ym' between check-in and check-out."""
    if not check_in_time or not check_out_time:
        return None
    start = timedelta(
        hours=check_in_time.hour, minutes=check_in_time.minute, seconds=check_in_time.second
    )
    end = timedelta(
        hours=check_out_time.hour, minutes=check_out_time.minute, seconds=check_out_time.second
    )
    diff = end - start
    if diff < timedelta(0):
        return None
    total_secs = int(diff.total_seconds())
    return f"{total_secs // 3600}h {(total_secs % 3600) // 60}m"


# --------------------------
# --------------------------
@login_required(login_url="admin_login")
def list_items(request, model, template, context_name):
    if request.user.is_staff:
        items = model.objects.all()
        return render(request, template, {context_name: items})
    return redirect("admin_login")


@login_required(login_url="admin_login")
def add_item(request, model, fields, template, redirect_url):
    if request.user.is_staff:
        if request.method == "POST":
            data = {field: request.POST[field] for field in fields}
            model.objects.create(**data)
            return redirect(redirect_url)
        return render(request, template)
    return redirect("admin_login")


@login_required(login_url="admin_login")
def edit_item(request, model, sl, fields, template, redirect_url):
    if request.user.is_staff:
        item = get_object_or_404(model, sl=sl)
        if request.method == "POST":
            for field in fields:
                setattr(item, field, request.POST[field])
            item.save()
            return redirect(redirect_url)
        return render(request, template, {model.__name__.lower(): item})
    return redirect("admin_login")


@login_required(login_url="admin_login")
def delete_item(request, model, sl, redirect_url):
    if request.user.is_staff:
        item = get_object_or_404(model, sl=sl)
        item.delete()
        return redirect(redirect_url)
    return redirect("admin_login")


# ============================================================
# ADMIN - EMPLOYEE CRUD
# ============================================================
def employee_list(request):
    return list_items(request, Employee, "employee_list.html", "employees")


def employee_add(request):
    if not request.user.is_staff:
        return redirect("admin_login")
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        position = request.POST.get("position", "Worker").strip()
        salary = request.POST.get("salary", "10000").strip()
        gender = request.POST.get("gender", "Male").strip()
        password = request.POST.get("password", "").strip()

        if not name or not email or not password:
            messages.error(request, "Name, email, and password are required.")
            return render(request, "employee_add.html")

        fmt_err = validate_email_format(email)
        if fmt_err:
            messages.error(request, fmt_err)
            return render(request, "employee_add.html")
        dup_err = email_already_exists(email)
        if dup_err:
            messages.error(request, dup_err)
            return render(request, "employee_add.html")

        try:
            phone_int = int(phone) if phone else 0
        except ValueError:
            messages.error(request, "Phone must be a valid number.")
            return render(request, "employee_add.html")

        try:
            salary_int = int(salary) if salary else 10000
        except ValueError:
            salary_int = 10000

        emp = Employee.objects.create(
            name=name,
            email=email,
            phone=phone_int,
            position=position,
            salary=salary_int,
            gender=gender,
            password=make_password(password),
            must_change_password=True,
        )
        user = User.objects.create_user(username=email, email=email, password=password)
        EmployeeProfile.objects.create(
            user=user, phone=str(phone_int), designation=position, employee=emp
        )
        messages.success(request, f"Employee '{name}' created. They must change password on first login.")
        return redirect("employee_list")
    return render(request, "employee_add.html")


def employee_edit(request, sl):
    if not request.user.is_staff:
        return redirect("admin_login")
    employee = get_object_or_404(Employee, sl=sl)
    if request.method == "POST":
        employee.name = request.POST.get("name", employee.name)
        employee.email = request.POST.get("email", employee.email)
        employee.position = request.POST.get("position", employee.position)
        employee.gender = request.POST.get("gender", employee.gender)
        salary_val = request.POST.get("salary", "")
        try:
            employee.salary = int(salary_val) if salary_val else employee.salary
        except ValueError:
            pass
        phone = request.POST.get("phone", "").strip()
        if phone:
            employee.phone = phone
        pw = request.POST.get("password", "")
        if pw:
            employee.password = make_password(pw)
            employee.must_change_password = True
            user = User.objects.filter(email=employee.email).first()
            if user:
                user.set_password(pw)
                user.save()
        employee.save()
        messages.success(request, "Employee updated successfully.")
        return redirect("employee_list")
    return render(request, "employee_edit.html", {"employee": employee})


def employee_delete(request, sl):
    return delete_item(request, Employee, sl, "employee_data")


# ============================================================
# ADMIN - BUYER CRUD
# ============================================================
def customer_list(request):
    return list_items(request, Customer, "customer_list.html", "customers")


def customer_add(request):
    if request.user.is_staff:
        if request.method == "POST":
            pw = request.POST.get("password")
            Customer.objects.create(
                name=request.POST.get("name"),
                email=request.POST.get("email"),
                phone=request.POST.get("phone"),
                address=request.POST.get("address"),
                password=make_password(pw) if pw else make_password("changeme123"),
            )
            return redirect("customer_list")
        return render(request, "customer_add.html")
    return redirect("admin_login")


def customer_edit(request, pk):
    if request.user.is_staff:
        customer = get_object_or_404(Customer, id=pk)
        if request.method == "POST":
            customer.name = request.POST.get("name", customer.name)
            customer.email = request.POST.get("email", customer.email)
            customer.phone = request.POST.get("phone", customer.phone)
            customer.address = request.POST.get("address", customer.address)
            pw = request.POST.get("password")
            if pw:
                customer.password = make_password(pw)
            customer.save()
            return redirect("customer_list")
        return render(request, "customer_edit.html", {"customer": customer})
    return redirect("admin_login")


def customer_delete(request, pk):
    if request.user.is_staff:
        customer = get_object_or_404(Customer, id=pk)
        customer.delete()
        return redirect("customer_list")
    return redirect("admin_login")



# ============================================================
# ADMIN - PRODUCT CRUD
# ============================================================
def product_edit(request, sl):
    product = Product.objects.get(sl=sl)

    if request.method == "POST":
        product.category = request.POST.get("category")
        product.subcategory = request.POST.get("subcategory")
        product.name = request.POST.get("name")
        product.brand = request.POST.get("brand", "").strip()
        product.sku = request.POST.get("sku", "").strip()
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")

        discount_val = request.POST.get("discount_price")
        try:
            product.discount_price = float(discount_val) if discount_val else None
        except (ValueError, TypeError):
            product.discount_price = None

        stock_val = request.POST.get("stock")
        try:
            new_stock = int(stock_val) if stock_val else 0
        except (ValueError, TypeError):
            new_stock = 0

        stock_changed = new_stock != product.stock
        previous_stock = product.stock
        product.stock = new_stock

        if request.FILES.get("image"):
            product.image = request.FILES.get("image")

        if product.stock <= 0:
            messages.warning(
                request,
                "This product is currently out of stock.",
            )

        product.save()

        if stock_changed:
            log_inventory(
                product=product,
                transaction_type="adjustment",
                quantity=abs(new_stock - previous_stock),
                previous_stock=previous_stock,
                new_stock=new_stock,
                reason="Stock updated via product edit",
                performed_by=request.user.username if request.user.is_authenticated else "Admin",
            )

        # Multiple image upload
        images = request.FILES.getlist("images")
        has_existing = product.images.exists()
        for idx, f in enumerate(images):
            ProductImage.objects.create(
                product=product, image=f, is_primary=(idx == 0 and not has_existing)
            )

        messages.success(request, "Product updated successfully.")
        return redirect("product_data")
    return render(request, "product_edit.html", {
        "product": product,
        "categories": Product.CATEGORY_CHOICES,
        "subcategories": Product.SUBCATEGORY_CHOICES,
    })


def product_image_delete(request, image_id):
    if not request.user.is_staff:
        return redirect("admin_login")
    image = get_object_or_404(ProductImage, id=image_id)
    product_sl = image.product.sl
    image.image.delete(save=False)
    image.delete()
    messages.success(request, "Product image removed.")
    return redirect("product_edit", sl=product_sl)


def product_image_set_primary(request, image_id):
    if not request.user.is_staff:
        return redirect("admin_login")
    image = get_object_or_404(ProductImage, id=image_id)
    ProductImage.objects.filter(product=image.product).update(is_primary=False)
    image.is_primary = True
    image.save()
    messages.success(request, "Primary image updated.")
    return redirect("product_edit", sl=image.product.sl)


def remove_from_cart(request, item_id):
    try:
        item = Cart.objects.get(id=item_id)
        item.delete()
    except Cart.DoesNotExist:
        pass

    return redirect("customer_dashboard")


def product_delete(request, sl):
    if request.user.is_staff:
        item = get_object_or_404(Product, sl=sl)
        item.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect("product_data")
    return redirect("admin_login")


@login_required(login_url="admin_login")
def product_variants(request, sl):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    product = get_object_or_404(Product, sl=sl)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_color":
            name = (request.POST.get("name") or "").strip()
            if name:
                ProductColor.objects.get_or_create(product=product, name=name)
                messages.success(request, f"Color '{name}' added.")
        elif action == "add_size":
            name = (request.POST.get("name") or "").strip()
            if name:
                ProductSize.objects.get_or_create(product=product, name=name)
                messages.success(request, f"Size '{name}' added.")
        elif action == "add_textile":
            name = (request.POST.get("name") or "").strip()
            if name:
                ProductTextile.objects.get_or_create(product=product, name=name)
                messages.success(request, f"Textile '{name}' added.")
        elif action == "add_variant":
            color = (request.POST.get("color") or "").strip()
            size = (request.POST.get("size") or "").strip()
            textile = (request.POST.get("textile") or "").strip()
            try:
                price = float(request.POST.get("price", 0) or 0)
                stock = int(request.POST.get("stock", 0) or 0)
            except (TypeError, ValueError):
                price, stock = 0, 0
            if color and size and textile:
                ProductVariant.objects.update_or_create(
                    product=product,
                    color=color,
                    size=size,
                    textile=textile,
                    defaults={"price": price, "stock": stock},
                )
                messages.success(request, "Variant saved.")
            else:
                messages.error(request, "Select a color, size and textile to create a variant.")
        elif action == "delete_variant":
            ProductVariant.objects.filter(id=request.POST.get("variant_id"), product=product).delete()
            messages.success(request, "Variant deleted.")
        elif action == "delete_color":
            ProductColor.objects.filter(id=request.POST.get("option_id"), product=product).delete()
            messages.success(request, "Color deleted.")
        elif action == "delete_size":
            ProductSize.objects.filter(id=request.POST.get("option_id"), product=product).delete()
            messages.success(request, "Size deleted.")
        elif action == "delete_textile":
            ProductTextile.objects.filter(id=request.POST.get("option_id"), product=product).delete()
            messages.success(request, "Textile deleted.")

        return redirect("product_variants", sl=product.sl)

    variants = product.variants.all().order_by("color", "size", "textile")
    colors = product.colors.all()
    sizes = product.sizes.all()
    textiles = product.textiles.all()

    return render(request, "product_variants.html", {
        "product": product,
        "variants": variants,
        "colors": colors,
        "sizes": sizes,
        "textiles": textiles,
    })


# --------------------------
@login_required(login_url="admin_login")
# ============================================================
# ADMIN - DATA VIEWS
# ============================================================
def employee_data(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    q = request.GET.get("q", "").strip()
    dept_filter = request.GET.get("department", "").strip()
    position_filter = request.GET.get("position", "").strip()

    profiles = EmployeeProfile.objects.select_related(
        "employee", "department", "job_position"
    )
    if q:
        profiles = profiles.filter(
            Q(employee__name__icontains=q)
            | Q(employee__email__icontains=q)
            | Q(employee__phone__icontains=q)
            | Q(employee__position__icontains=q)
            | Q(public_id__icontains=q)
        )
    if dept_filter:
        profiles = profiles.filter(department_id=dept_filter)
    if position_filter:
        profiles = profiles.filter(job_position_id=position_filter)

    employees = [p.employee for p in profiles]
    for p in profiles:
        p.employee.employeeprofile = p

    return render(request, "employees_data.html", {
        "employees": employees,
        "q": q,
        "dept_filter": dept_filter,
        "position_filter": position_filter,
        "departments": Department.objects.all(),
        "job_positions": JobPosition.objects.all(),
    })



@login_required(login_url="admin_login")
# ============================================================
#                 RAW MATERIALS (Yardage)
# ============================================================
@login_required(login_url="admin_login")
def product_data(request):
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    subcategory = request.GET.get("subcategory", "").strip()
    stock_status = request.GET.get("stock", "").strip()
    sort = request.GET.get("sort", "").strip()

    products = Product.objects.prefetch_related("images", "variants", "colors", "sizes", "textiles")

    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__icontains=q)
            | Q(subcategory__icontains=q)
            | Q(brand__icontains=q)
            | Q(sku__icontains=q)
        )
    if category:
        products = products.filter(category=category)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if stock_status == "low":
        products = products.filter(stock__lte=F("low_stock_threshold"), stock__gt=0)
    elif stock_status == "out":
        products = products.filter(stock=0)
    elif stock_status == "available":
        products = products.filter(stock__gt=0)

    if sort == "price_low":
        products = products.order_by("price")
    elif sort == "price_high":
        products = products.order_by("-price")
    elif sort == "name":
        products = products.order_by("name")
    elif sort == "newest":
        products = products.order_by("-sl")
    else:
        products = products.order_by("name")

    return render(
        request,
        "product_data.html",
        {
            "products": products,
            "q": q,
            "selected_category": category,
            "selected_subcategory": subcategory,
            "stock_status": stock_status,
            "sort": sort,
            "categories": Product.CATEGORY_CHOICES,
            "subcategories": Product.SUBCATEGORY_CHOICES,
        },
    )


# --------------------------
# --------------------------
# ============================================================
# PUBLIC PAGES
# ============================================================
def index(request):
    return render(request, "index.html")


def about(request):
    return render(request, "about.html")


# ============================================================
# REGISTRATION VIEWS
# ============================================================


def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            emp = Employee.objects.get(email=email)
            if check_password(password, emp.password):
                request.session["employee_id"] = emp.sl
                return redirect("dashboard")
        except (Employee.DoesNotExist, ValueError):
            pass

        messages.error(request, "Invalid email or password")
        return redirect("login_page")

    return render(request, "login.html")


def employee_change_password(request):
    employee_id = request.session.get("employee_id")
    if not employee_id:
        return redirect("login_page")
    emp = Employee.objects.get(sl=employee_id)
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not check_password(current_password, emp.password):
            messages.error(request, "Current password is incorrect.")
            return render(request, "employee_change_password.html")

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return render(request, "employee_change_password.html")

        errors = validate_strong_password(new_password)
        if errors:
            messages.error(request, " ".join(errors))
            return render(request, "employee_change_password.html")

        emp.password = make_password(new_password)
        emp.must_change_password = False
        emp.save()
        user = User.objects.filter(email=emp.email).first()
        if user:
            user.set_password(new_password)
            user.save()
        messages.success(request, "Password changed successfully. Please log in again.")
        return redirect("login_page")
    return render(request, "employee_change_password.html")



# -------------------------------------------------------#
#                    Customer parts                         #
# -------------------------------------------------------#


# ============================================================
# BUYER AUTH & PROFILE
# ============================================================
def customer_register_page(request):
    form = CustomerRegisterForm()
    return render(request, "customer-register.html", {"form": form})


def customer_register(request):
    if request.method == "POST":
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.password = make_password(form.cleaned_data["password"])
            customer.save()
            messages.success(
                request, "Customer account created successfully. Please log in."
            )
            return redirect("customer_login_page")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}" if field != "__all__" else err)
            return redirect("customer_register_page")
    return redirect("customer_register_page")


def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("customer_id"):
            return redirect("customer_login_page")
        return view_func(request, *args, **kwargs)

    return wrapper


def employee_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("employee_id"):
            return redirect("login_page")
        return view_func(request, *args, **kwargs)

    return wrapper


def customer_login_page(request):
    form = CustomerLoginForm()
    return render(request, "customer-login.html", {"form": form})


def customer_login(request):

    if request.method == "POST":
        form = CustomerLoginForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            customer = Customer.objects.filter(email=email).first()

            if customer and check_password(password, customer.password):
                request.session["customer_id"] = customer.id
                request.session["customer_name"] = customer.name

                messages.success(request, f"Welcome {customer.name}")

                return redirect("customer_dashboard")

            else:
                messages.error(request, "Invalid email or password")
                return redirect("customer_login_page")
    else:
        form = CustomerLoginForm()

    return render(request, "customer-login.html", {"form": form})


def customer_logout(request):
    request.session.pop("customer_id", None)
    request.session.pop("customer_name", None)
    return redirect("index")


def customer_dashboard(request):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    customer = get_object_or_404(Customer, id=customer_id)

    products = Product.objects.all()

    # Category Filter
    category = request.GET.get("category")
    if category:
        products = products.filter(category=category)

    # Subcategory Filter
    subcategory = request.GET.get("subcategory")
    if subcategory:
        products = products.filter(subcategory=subcategory)

    cart_items = Cart.objects.filter(customer=customer).select_related("product")

    cart_total = sum(item.subtotal for item in cart_items)

    orders = Order.objects.filter(customer=customer).order_by("-created_at")

    return render(
        request,
        "customer-dashboard.html",
        {
            "customer": customer,
            "products": products,
            "orders": orders,
            "cart_items": cart_items,
            "cart_total": cart_total,
        },
    )
    
def customer_profile(request):
    customer = Customer.objects.get(id=request.session["customer_id"])
    return render(request, "customer_profile.html", {"customer": customer})

def edit_customer_profile(request):
    customer = Customer.objects.get(id=request.session["customer_id"])

    if request.method == "POST":
        customer.name = request.POST.get("name")
        customer.phone = request.POST.get("phone")

        if request.FILES.get("photo"):
            customer.photo = request.FILES["photo"]
            print("PHOTO:", customer.photo)
        else:
            print("NO PHOTO RECEIVED")

        customer.save()

        return redirect("customer_profile")

    return render(request, "edit_customer_profile.html", {
        "customer": customer
    })

def product_list(request):
    category = request.GET.get("category", "").strip()
    subcategory = request.GET.get("subcategory", "").strip()
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "").strip()

    products = Product.objects.prefetch_related("images", "colors", "variants")

    if category:
        products = products.filter(category=category)
    if subcategory:
        products = products.filter(subcategory=subcategory)
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(brand__icontains=q)
            | Q(description__icontains=q)
            | Q(subcategory__icontains=q)
        )

    # In-stock first, then out-of-stock at the end (like the reference site)
    if sort == "price_low":
        products = products.order_by("price")
    elif sort == "price_high":
        products = products.order_by("-price")
    elif sort == "name":
        products = products.order_by("name")
    elif sort == "newest":
        products = products.order_by("-sl")
    else:
        products = products.order_by("-stock", "name")

    subcategories = [
        (value, label)
        for value, label in Product.SUBCATEGORY_CHOICES
        if not category or value in Product.objects.filter(category=category).values_list("subcategory", flat=True)
    ]

    return render(request, "product-list.html", {
        "products": products,
        "category": category,
        "subcategory": subcategory,
        "q": q,
        "sort": sort,
        "subcategories": subcategories,
    })


def product_add(request):
    if request.method == "POST":
        stock_val = request.POST.get("stock")
        try:
            stock = int(stock_val) if stock_val else 0
        except (ValueError, TypeError):
            stock = 0

        price_val = request.POST.get("price")
        try:
            price = float(price_val) if price_val else 0
        except (ValueError, TypeError):
            price = 0

        discount_val = request.POST.get("discount_price")
        try:
            discount_price = float(discount_val) if discount_val else None
        except (ValueError, TypeError):
            discount_price = None

        product = Product.objects.create(
            name=request.POST.get("name"),
            brand=request.POST.get("brand", "").strip(),
            sku=request.POST.get("sku", "").strip(),
            description=request.POST.get("description"),
            price=price,
            discount_price=discount_price,
            stock=stock,
            category=request.POST.get("category"),
            subcategory=request.POST.get("subcategory"),
            image=request.FILES.get("image"),
        )

        # Multiple image upload
        images = request.FILES.getlist("images")
        for idx, f in enumerate(images):
            ProductImage.objects.create(
                product=product, image=f, is_primary=(idx == 0)
            )

        if stock:
            log_inventory(
                product=product,
                transaction_type="increase",
                quantity=stock,
                previous_stock=0,
                new_stock=stock,
                reason="Initial stock on product creation",
                performed_by=request.user.username if request.user.is_authenticated else "Admin",
            )

        messages.success(request, "Product added successfully.")
        return redirect("product_data")

    return render(request, "product_add.html", {
        "categories": Product.CATEGORY_CHOICES,
        "subcategories": Product.SUBCATEGORY_CHOICES,
    })


def bdt(value):
    try:
        return f"\u09F3{float(value):,.0f}"
    except (TypeError, ValueError):
        return "\u09F30"


def cart_item_stock(cart_item):
    """Stock available for a cart item's selected variant (or base product)."""
    if cart_item.color or cart_item.size or cart_item.textile:
        variant = ProductVariant.objects.filter(
            product=cart_item.product,
            color=cart_item.color,
            size=cart_item.size,
            textile=cart_item.textile,
        ).first()
        if variant:
            return variant.stock
    return cart_item.product.stock


def product_detail(request, sl):
    product = get_object_or_404(Product, sl=sl)
    variants = list(product.variants.all())
    has_variants = bool(variants)

    colors = list(product.colors.all().values_list("name", flat=True))
    sizes = list(product.sizes.all().values_list("name", flat=True))
    textiles = list(product.textiles.all().values_list("name", flat=True))

    variant_data = [
        {"color": v.color, "size": v.size, "textile": v.textile,
         "price": float(v.price), "stock": v.stock}
        for v in variants
    ]

    images = list(product.images.all())
    gallery = images if images else ([product.image] if product.image else [])

    related = Product.objects.filter(
        Q(category=product.category) | Q(subcategory=product.subcategory)
    ).exclude(sl=product.sl).distinct()[:8]

    in_cart_qty = 0
    if request.session.get("customer_id"):
        in_cart_qty = sum(
            c.quantity
            for c in Cart.objects.filter(customer_id=request.session["customer_id"], product=product)
        )

    return render(request, "product-detail.html", {
        "product": product,
        "colors": colors,
        "sizes": sizes,
        "textiles": textiles,
        "has_variants": has_variants,
        "variants_json": json.dumps(variant_data),
        "base_price": bdt(product.effective_price),
        "base_original_price": bdt(product.price),
        "discount_percent": product.discount_percent,
        "base_stock": product.stock,
        "gallery": gallery,
        "related": related,
        "in_cart_qty": in_cart_qty,
    })


def customer_cart_page(request):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    customer = get_object_or_404(Customer, id=customer_id)
    cart_items = Cart.objects.filter(customer=customer).select_related("product")

    for item in cart_items:
        item.variant_stock = cart_item_stock(item)

    cart_total = sum(item.subtotal for item in cart_items)
    total_quantity = sum(item.quantity for item in cart_items)

    return render(request, "cart.html", {
        "customer": customer,
        "cart_items": cart_items,
        "cart_total": cart_total,
        "total_quantity": total_quantity,
    })


def _add_item_to_cart(customer, product, color, size, textile, qty):
    has_variants = product.variants.exists()

    variant = None
    if has_variants and color and size and textile:
        variant = ProductVariant.objects.filter(
            product=product, color=color, size=size, textile=textile
        ).first()
        if not variant:
            return False, "This combination is not available. Please choose another option.", None
    elif has_variants and (color or size or textile):
        # partial selection -> ignore options and use the base product
        color = size = textile = ""

    if variant:
        available = variant.stock
        unit_price = variant.price
    else:
        available = product.stock
        unit_price = product.effective_price

    if available <= 0:
        return False, "This product is currently out of stock.", None

    if qty > available:
        return False, f"Only {available} items are available for this variant.", None

    cart_item, created = Cart.objects.get_or_create(
        customer=customer,
        product=product,
        color=color,
        size=size,
        textile=textile,
        defaults={"quantity": qty, "unit_price": unit_price},
    )

    if not created:
        new_qty = cart_item.quantity + qty
        if new_qty > available:
            return False, f"Only {available} items are available for this variant.", None
        cart_item.quantity = new_qty
        cart_item.unit_price = unit_price
        cart_item.save()

    return True, "", cart_item


def add_to_cart(request, product_id):

    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    customer = Customer.objects.get(id=customer_id)
    product = get_object_or_404(Product, sl=product_id)

    if request.method != "POST":
        return redirect("product_detail", sl=product.sl)

    color = (request.POST.get("color") or "").strip()
    size = (request.POST.get("size") or "").strip()
    textile = (request.POST.get("textile") or "").strip()

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    if qty < 1:
        qty = 1

    ok, msg, _ = _add_item_to_cart(customer, product, color, size, textile, qty)
    if not ok:
        messages.error(request, msg)
        return redirect("product_detail", sl=product.sl)

    messages.success(request, f"{product.name} added to cart.")
    return redirect("product_detail", sl=product.sl)


def buy_now(request, product_id):

    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    customer = Customer.objects.get(id=customer_id)
    product = get_object_or_404(Product, sl=product_id)

    if request.method != "POST":
        return redirect("product_detail", sl=product.sl)

    color = (request.POST.get("color") or "").strip()
    size = (request.POST.get("size") or "").strip()
    textile = (request.POST.get("textile") or "").strip()

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    if qty < 1:
        qty = 1

    has_variants = product.variants.exists()

    # Buy Now validates the full variant selection before adding to the cart
    if has_variants and not (color and size and textile):
        messages.error(request, "Please select color, size and textile before buying.")
        return redirect("product_detail", sl=product.sl)

    ok, msg, cart_item = _add_item_to_cart(customer, product, color, size, textile, qty)
    if not ok:
        messages.error(request, msg)
        return redirect("product_detail", sl=product.sl)

    messages.success(request, f"{product.name} added to your cart. Complete your order below.")
    return redirect(f"{reverse('checkout')}?cart_id={cart_item.id}")


def update_cart(request, cart_id):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    cart_item = get_object_or_404(Cart, id=cart_id, customer_id=customer_id)
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", cart_item.quantity))
        except (TypeError, ValueError):
            quantity = cart_item.quantity

        if quantity < 1:
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        else:
            available = cart_item_stock(cart_item)
            if quantity > available:
                messages.error(request, f"Only {available} items are available for this variant.")
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, "Cart updated successfully.")

    next_url = request.POST.get("next", "customer_dashboard")
    try:
        return redirect(next_url)
    except Exception:
        return redirect("customer_dashboard")


def remove_cart(request, cart_id):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    cart_item = get_object_or_404(Cart, id=cart_id, customer_id=customer_id)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")

    next_url = request.POST.get("next") or request.GET.get("next") or "customer_dashboard"
    try:
        return redirect(next_url)
    except Exception:
        return redirect("customer_dashboard")


def customer_checkout(request):
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    customer = get_object_or_404(Customer, id=customer_id)
    cart_items = Cart.objects.filter(customer=customer).select_related("product")
    if not cart_items:
        messages.info(request, "Your cart is empty. Add products before checkout.")
        return redirect("customer_dashboard")

    total_quantity = sum(item.quantity for item in cart_items)
    if total_quantity > 7:
        messages.error(
            request,
            "You can purchase a maximum of 7 items in a single order. Please reduce the quantity before proceeding.",
        )
        return redirect("customer_cart")

    total_amount = sum(item.subtotal for item in cart_items)
    if total_amount <= 0:
        messages.error(request, "Unable to process checkout for zero total amount.")
        return redirect("customer_dashboard")

    order_ids = []
    for cart_item in cart_items:
        order = Order.objects.create(
            customer=customer,
            product=cart_item.product,
            quantity=cart_item.quantity,
            total_amount=cart_item.subtotal,
            status="Pending",
            color=cart_item.color,
            size=cart_item.size,
            textile=cart_item.textile,
            unit_price=cart_item.price,
        )
        order_ids.append(order.id)

    tran_id = f"CHECKOUT-{uuid.uuid4().hex[:16].upper()}"
    txn = PaymentTransaction.objects.create(
        order_id=tran_id,
        customer=customer,
        amount=total_amount,
        currency="BDT",
        status="pending",
        metadata={"order_ids": order_ids},
    )

    success_url = request.build_absolute_uri(reverse("payment_success"))
    fail_url = request.build_absolute_uri(reverse("payment_fail"))
    api_url = getattr(
        settings,
        "SSLCOMMERZ_API_URL",
        "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
    )

    payload = {
        "store_id": getattr(settings, "SSL_COMMERZ_STORE_ID", ""),
        "store_passwd": getattr(settings, "SSL_COMMERZ_STORE_PASSWORD", ""),
        "total_amount": str(total_amount),
        "currency": "BDT",
        "tran_id": tran_id,
        "success_url": success_url,
        "fail_url": fail_url,
        "cancel_url": fail_url,
        "cus_name": customer.name,
        "cus_email": customer.email,
        "cus_phone": customer.phone,
        "product_name": "Multiple items",
        "product_category": "Fashion",
        "product_profile": "general",
    }

    try:
        response = requests.post(api_url, data=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        gateway_url = data.get("GatewayPageURL")
        if gateway_url:
            cart_items.delete()
            return redirect(gateway_url)
        txn.status = "failed"
        txn.metadata = {"error": data}
        txn.save()
        messages.error(request, data.get("failedreason", "Payment gateway error"))
    except requests.RequestException as exc:
        txn.status = "failed"
        txn.metadata = {"error": str(exc)}
        txn.save()
        messages.error(request, f"Payment gateway error: {str(exc)}")

    return redirect("customer_dashboard")
# --------------------------
def password_reset_request(request, role=""):
    role_filter = role or request.GET.get("role", "")
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            found = False
            role = None

            if role_filter == "employee" or not role_filter:
                if Employee.objects.filter(email=email).exists():
                    found = True
                    role = "employee"
            if role_filter == "customer" or (not role_filter and not found):
                if Customer.objects.filter(email=email).exists():
                    found = True
                    role = "customer"
            if role_filter == "admin" or (not role_filter and not found):
                if User.objects.filter(email=email, is_staff=True).exists():
                    found = True
                    role = "admin"

            if found:
                PasswordResetToken.objects.filter(
                    email=email, role=role, is_used=False
                ).delete()
                raw_token = secrets.token_urlsafe(16)
                PasswordResetToken.objects.create(
                    email=email,
                    role=role,
                    token=make_password(raw_token),
                )
                reset_link = request.build_absolute_uri(
                    reverse("password_reset_confirm", args=[raw_token])
                )
                try:
                    send_mail(
                        subject="Password Reset Request - Touch and Solve",
                        message=f"Hello,\n\nYou requested a password reset.\n\nClick the link below to set a new password (the link expires in 1 hour):\n<{reset_link}>\n\nIf you did not request this, please ignore this email.\n\n- Touch and Solve Team",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception:
                    messages.error(request, "Could not send reset email. Please try again later.")
                    return render(request, "password_reset.html", {"form": form, "role": role_filter})
            messages.success(request, "If an account with that email exists, a reset link has been sent.")
            return redirect("index")
    else:
        form = PasswordResetRequestForm()
    return render(request, "password_reset.html", {"form": form, "role": role_filter})


def password_reset_confirm(request, token):
    tokens = PasswordResetToken.objects.filter(is_used=False)
    valid_token = None
    for t in tokens:
        if check_password(token, t.token) and not t.is_expired():
            valid_token = t
            break

    if not valid_token:
        messages.error(request, "Invalid or expired reset link. Please request a new one.")
        return redirect("password_reset_request")

    if request.method == "POST":
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            hashed = make_password(new_password)

            if valid_token.role == "employee":
                Employee.objects.filter(email=valid_token.email).update(password=hashed)
                user = User.objects.filter(email=valid_token.email).first()
                if user:
                    user.set_password(new_password)
                    user.save()
            elif valid_token.role == "customer":
                Customer.objects.filter(email=valid_token.email).update(password=hashed)
            elif valid_token.role == "admin":
                user = User.objects.filter(email=valid_token.email, is_staff=True).first()
                if user:
                    user.set_password(new_password)
                    user.save()

            valid_token.is_used = True
            valid_token.save()
            messages.success(request, "Password reset successful. Please log in.")
            login_page_map = {
                "employee": "login_page",
                "customer": "customer_login_page",
                "admin": "admin_login",
            }
            return redirect(login_page_map.get(valid_token.role, "login_page"))
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
            return render(request, "set_new_password.html", {"form": form, "token": token, "role": valid_token.role})

    form = SetPasswordForm()
    return render(request, "set_new_password.html", {"form": form, "token": token, "role": valid_token.role})




# --------------------------
# Admin
# --------------------------
# ============================================================
# ADMIN AUTH & DASHBOARD
# ============================================================
def custom_admin_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                return redirect("employee_list")
            else:
                return redirect("login")
    else:
        form = AuthenticationForm()

    return render(request, "admin_login.html", {"form": form})


@login_required(login_url="admin_login")
def admin_redirect(request):
    if request.user.is_authenticated and request.user.is_staff:
        from datetime import datetime
        from .models import Product, Customer, Order, PaymentTransaction

        employees = Employee.objects.annotate(
            total_production=Sum("production__quantity")
        )

        # Get current month and year
        current_date = timezone.now()
        month_start = current_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)

        # Find employees who HAVE been paid this month
        paid_employee_ids = (
            PaymentTransaction.objects.filter(
                employee__isnull=False,
                status="success",
                created_at__gte=month_start,
                created_at__lt=month_end,
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )

        # Attach payment_status to each employee
        for emp in employees:
            emp.payment_status = "Paid" if emp.sl in paid_employee_ids else "Unpaid"

        from .models import Order
        order_count = Order.objects.count()

        today = timezone.localdate()
        today_attendance = Attendance.objects.filter(date=today).select_related(
            "employee__employee"
        ).order_by("employee__employee__name")

        late_count = today_attendance.filter(status="Late").count()
        all_profiles = EmployeeProfile.objects.select_related("employee").all()
        attended_ids = set(today_attendance.values_list("employee_id", flat=True))
        absent_profiles = [p for p in all_profiles if p.id not in attended_ids]

        payroll_rows = [monthly_payroll_for(p, today.year, today.month) for p in all_profiles]
        payroll_totals = {
            "basic": sum(r["basic"] for r in payroll_rows),
            "deduction": sum(r["total_deduction"] for r in payroll_rows),
            "overtime": sum(r["overtime_amount"] for r in payroll_rows),
            "net": sum(r["net"] for r in payroll_rows),
            "paid": sum(1 for r in payroll_rows if r["paid"]),
            "pending": sum(1 for r in payroll_rows if not r["paid"]),
        }

        return render(
            request,
            "admin_dashboard.html",
            {
                "employees": employees,
                "products": Product.objects.all(),
                "order_count": order_count,
                "today_attendance": today_attendance,
                "late_count": late_count,
                "absent_profiles": absent_profiles,
                "payroll_totals": payroll_totals,
                "payroll_month": today.strftime("%Y-%m"),
            },
        )
    return redirect("admin_login")


@login_required(login_url="admin_login")
@login_required(login_url="admin_login")
def admin_order_list(request):
    from .models import Order
    orders = Order.objects.all().select_related("customer", "product").order_by("-created_at")

    # Fetch pending cancellation requests
    cancellation_requests = CancellationRequest.objects.filter(
        status="Pending"
    ).select_related("order", "customer")

    return render(request, "admin_orders.html", {
        "orders": orders,
        "cancellation_requests": cancellation_requests,
    })


@login_required(login_url="admin_login")
def mark_order_sent(request, order_id):
    from .models import Order
    order = get_object_or_404(Order, id=order_id)
    if order.status in ('Cancelled', 'Returned', 'Delivered'):
        messages.error(request, f"Cannot send order #{order.id} — it is {order.status}.")
        return redirect("admin_order_list")
    order.status = "Sent"
    order.save()
    messages.success(request, f"Order #{order.id} marked as Sent.")
    return redirect("admin_order_list")


@login_required(login_url="admin_login")
def mark_order_status(request, order_id):
    """Admin: manually update order status (e.g., In Production)."""
    if request.method != "POST":
        return redirect("admin_order_list")
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get("status", "")
    valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, "Invalid status.")
        return redirect("admin_order_list")
    order.status = new_status
    order.save()
    messages.success(request, f"Order #{order.id} status updated to {new_status}.")
    return redirect("admin_order_list")


# ============================================================
# BUYER - ORDER CANCELLATION
# ============================================================
def customer_cancel_order(request, order_id):
    """Customer requests order cancellation based on status policy."""
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    order = get_object_or_404(Order, id=order_id, customer_id=customer_id)

    if order.status == 'Pending':
        # Pending (unpaid/COD) — customer can cancel directly
        with transaction.atomic():
            product_locked = Product.objects.select_for_update().get(sl=order.product.sl)
            previous_stock = product_locked.stock
            product_locked.stock += order.quantity
            product_locked.save()
            log_inventory(
                product=product_locked,
                transaction_type="increase",
                quantity=order.quantity,
                previous_stock=previous_stock,
                new_stock=product_locked.stock,
                reason=f"Cancellation of Order #{order.id} (Pending)",
                performed_by="Customer",
            )
        order.status = 'Cancelled'
        order.save()
        messages.success(request, f"Order #{order.id} has been cancelled successfully.")
        return redirect("orders_html")

    elif order.status == 'Paid':
        # Paid (SSLCommerz) — requires admin approval
        if CancellationRequest.objects.filter(order=order, status='Pending').exists():
            messages.info(request, "A cancellation request for this order is already pending.")
            return redirect("orders_html")
        reason = request.POST.get("reason", "") if request.method == "POST" else ""
        CancellationRequest.objects.create(
            order=order,
            customer=order.customer,
            reason=reason,
        )
        messages.success(request, f"Cancellation request for Order #{order.id} submitted. Awaiting admin approval.")
        return redirect("orders_html")

    elif order.status == 'In Production':
        messages.error(request, f"Order #{order.id} is in production. Cancellation is not allowed.")
        return redirect("orders_html")

    elif order.status == 'Sent':
        messages.info(request, f"Order #{order.id} has been shipped. Please use the return policy instead.")
        return redirect("orders_html")

    else:
        messages.info(request, f"Order #{order.id} is {order.status}. No action available.")
        return redirect("orders_html")


# ============================================================
# ADMIN - CANCELLATION REQUEST MANAGEMENT
# ============================================================
@login_required(login_url="admin_login")
def approve_cancellation(request, pk):
    """Admin approves a pending cancellation request — refunds stock."""
    if request.method != "POST":
        return redirect("admin_order_list")

    cancel_req = get_object_or_404(CancellationRequest, pk=pk, status="Pending")
    order = cancel_req.order

    with transaction.atomic():
        product_locked = Product.objects.select_for_update().get(sl=order.product.sl)
        previous_stock = product_locked.stock
        product_locked.stock += order.quantity
        product_locked.save()
        log_inventory(
            product=product_locked,
            transaction_type="increase",
            quantity=order.quantity,
            previous_stock=previous_stock,
            new_stock=product_locked.stock,
            reason=f"Cancellation of Order #{order.id} approved",
            performed_by=request.user.username,
        )

    order.status = 'Cancelled'
    order.save()
    cancel_req.status = 'Approved'
    cancel_req.resolved_at = timezone.now()
    cancel_req.admin_notes = request.POST.get("admin_notes", "")
    cancel_req.save()

    messages.success(request, f"Cancellation for Order #{order.id} approved. Stock restored.")
    return redirect("admin_order_list")


@login_required(login_url="admin_login")
def reject_cancellation(request, pk):
    """Admin rejects a pending cancellation request."""
    if request.method != "POST":
        return redirect("admin_order_list")

    cancel_req = get_object_or_404(CancellationRequest, pk=pk, status="Pending")
    cancel_req.status = 'Rejected'
    cancel_req.resolved_at = timezone.now()
    cancel_req.admin_notes = request.POST.get("admin_notes", "")
    cancel_req.save()

    messages.warning(request, f"Cancellation for Order #{cancel_req.order.id} rejected.")
    return redirect("admin_order_list")


# ============================================================
# BUYER - RETURN REQUEST
# ============================================================
def customer_return_order(request, order_id):
    """Customer requests a return for a shipped order."""
    customer_id = request.session.get("customer_id")
    if not customer_id:
        return redirect("customer_login_page")

    order = get_object_or_404(Order, id=order_id, customer_id=customer_id)

    if not order.can_be_returned:
        messages.error(request, f"Order #{order.id} cannot be returned — it is {order.status}.")
        return redirect("orders_html")

    order.status = 'Returned'
    order.save()

    # Restore stock
    with transaction.atomic():
        product_locked = Product.objects.select_for_update().get(sl=order.product.sl)
        previous_stock = product_locked.stock
        product_locked.stock += order.quantity
        product_locked.save()
        log_inventory(
            product=product_locked,
            transaction_type="increase",
            quantity=order.quantity,
            previous_stock=previous_stock,
            new_stock=product_locked.stock,
            reason=f"Return of Order #{order.id}",
            performed_by="Customer",
        )

    messages.success(request, f"Return for Order #{order.id} processed. Stock restored.")
    return redirect("orders_html")


@login_required(login_url="admin_login")
def admin_logout(request):
    auth_logout(request)
    request.session.flush()
    return redirect("admin_login")


def employee_profile(request):
    
    employee_id = request.session.get("employee_id")

    if not employee_id:
        return redirect("employee_login")

    profile = EmployeeProfile.objects.get(employee_id=employee_id)

    return render(
        request,
        "employee_profile.html",
        {"profile": profile}
    )
    
def edit_employee_profile(request):
    
    employee_id = request.session.get("employee_id")

    if not employee_id:
        return redirect("employee_login")

    profile = EmployeeProfile.objects.get(employee_id=employee_id)

    if request.method == "POST":

        profile.phone = request.POST.get("phone")

        profile.designation = request.POST.get("designation")

        if request.FILES.get("photo"):
            profile.photo = request.FILES["photo"]

        profile.save()

        return redirect("employee_profile")

    return render(
        request,
        "edit_employee_profile.html",
        {"profile": profile}
    )


def buy_product(request, product_id):
    product = get_object_or_404(Product, sl=product_id)
    customer_id = request.session.get("customer_id")
    if not customer_id:
        messages.info(request, "Please sign in to buy products.")
        return redirect("customer_login_page")

    customer = get_object_or_404(Customer, id=customer_id)
    error_message = None

    if request.method == "POST":
        try:
            qty = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            qty = 1

        if qty < 1:
            qty = 1

        # Atomic stock check and reservation
        with transaction.atomic():
            locked_product = Product.objects.select_for_update().get(sl=product_id)
            if locked_product.stock < qty:
                messages.error(
                    request,
                    f'Insufficient stock for "{locked_product.name}". Only {locked_product.stock} units available.',
                )
                return redirect("buy_product", product_id=product_id)

            previous_stock = locked_product.stock
            locked_product.stock -= qty
            locked_product.save()
            log_inventory(
                product=locked_product,
                transaction_type="decrease",
                quantity=qty,
                previous_stock=previous_stock,
                new_stock=locked_product.stock,
                reason=f"Order reservation by {customer.name}",
                performed_by="Customer",
            )

        total = product.price * qty

        order = Order.objects.create(
            customer=customer,
            product=product,
            quantity=qty,
            total_amount=total,
            status="Pending",
        )

        tran_id = f"ORDER-{uuid.uuid4().hex[:16].upper()}"
        PaymentTransaction.objects.create(
            order_id=tran_id,
            customer=customer,
            amount=total,
            currency="BDT",
            status="pending",
        )

        success_url = request.build_absolute_uri(reverse("payment_success"))
        fail_url = request.build_absolute_uri(reverse("payment_fail"))

        ssl_data = {
            "store_id": getattr(settings, "SSL_COMMERZ_STORE_ID", ""),
            "store_passwd": getattr(settings, "SSL_COMMERZ_STORE_PASSWORD", ""),
            "total_amount": str(total),
            "currency": "BDT",
            "tran_id": tran_id,
            "success_url": success_url,
            "fail_url": fail_url,
            "cancel_url": fail_url,
            "cus_name": customer.name,
            "cus_email": customer.email,
            "cus_phone": customer.phone,
            "product_name": product.name,
            "product_category": "Fashion",
            "product_profile": "general",
        }

        try:
            api_url = getattr(
                settings,
                "SSLCOMMERZ_API_URL",
                "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
            )
            response = requests.post(api_url, data=ssl_data, timeout=20)
            response.raise_for_status()
            data = response.json()
            gateway_url = data.get("GatewayPageURL")
            if gateway_url:
                return redirect(gateway_url)
            error_message = data.get(
                "failedreason", data.get("status", "Payment initiation failed")
            )
        except requests.RequestException as exc:
            error_message = f"Payment gateway error: {str(exc)}"
        except ValueError:
            error_message = "Payment gateway returned an invalid response."

    return render(
        request,
        "buy.html",
        {
            "product": product,
            "customer": customer,
            "error_message": error_message,
        },
    )


@login_required(login_url="admin_login")
def attendance_list(request):
    if request.user.is_authenticated and request.user.is_staff:
        attendances = Attendance.objects.select_related(
            "employee__employee"
        ).order_by("-date")

        q = request.GET.get("q", "").strip()
        month = request.GET.get("month", "").strip()
        date_filter = request.GET.get("date", "").strip()

        if q:
            attendances = attendances.filter(employee__employee__name__icontains=q)
        if month:
            try:
                y, m = month.split("-")
                attendances = attendances.filter(
                    date__year=int(y), date__month=int(m)
                )
            except ValueError:
                pass
        if date_filter:
            attendances = attendances.filter(date=date_filter)

        return render(
            request,
            "attendance_list.html",
            {
                "attendances": attendances,
                "q": q,
                "month": month,
                "date_filter": date_filter,
            },
        )
    return redirect("admin_login")


@login_required(login_url="admin_login")
def attendance_edit(request, pk):
    if request.user.is_authenticated and request.user.is_staff:
        attendance = get_object_or_404(Attendance, pk=pk)

        if request.method == "POST":
            form = AttendanceEditForm(request.POST, instance=attendance)
            if form.is_valid():
                form.save()
                messages.success(request, "Attendance updated.")
                return redirect("attendance_list")
        else:
            form = AttendanceEditForm(instance=attendance)

        return render(
            request, "attendance_edit.html", {"form": form, "attendance": attendance}
        )
    return redirect("admin_login")


@login_required(login_url="admin_login")
def office_ip_list(request):
    if request.user.is_authenticated and request.user.is_staff:
        form = OfficeIPForm()
        if request.method == "POST":
            form = OfficeIPForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Office IP added.")
                return redirect("office_ip_list")
        return render(
            request,
            "office_ips.html",
            {"ips": OfficeIP.objects.all(), "form": form},
        )
    return redirect("admin_login")


@login_required(login_url="admin_login")
def office_ip_edit(request, pk):
    if request.user.is_authenticated and request.user.is_staff:
        ip = get_object_or_404(OfficeIP, pk=pk)
        if request.method == "POST":
            form = OfficeIPForm(request.POST, instance=ip)
            if form.is_valid():
                form.save()
                messages.success(request, "Office IP updated.")
                return redirect("office_ip_list")
        else:
            form = OfficeIPForm(instance=ip)
        return render(
            request, "office_ip_edit.html", {"form": form, "ip": ip}
        )
    return redirect("admin_login")


@login_required(login_url="admin_login")
def office_ip_delete(request, pk):
    if request.user.is_authenticated and request.user.is_staff:
        ip = get_object_or_404(OfficeIP, pk=pk)
        ip.delete()
        messages.success(request, f"Office IP {ip.ip_address} deleted.")
    return redirect("office_ip_list")


@login_required(login_url="admin_login")
def employee_bonus(request):
    if request.user.is_authenticated and request.user.is_staff:
        employees = Employee.objects.all()
        if request.method == "POST":
            emp_id = request.POST.get("employee")
            bonus = request.POST.get("bonus")
            try:
                emp = Employee.objects.get(sl=emp_id)
                emp.salary = emp.salary + (emp.salary * int(bonus) / 100)
                emp.save()
            except Employee.DoesNotExist:
                pass
            return redirect("employee_list")

    return render(request, "employee_bonus.html", {"employees": employees})


# --------------------------
# Employee production
# --------------------------
# ============================================================
# EMPLOYEE DASHBOARD & PRODUCTION
# ============================================================
def dashboard(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login_page")
    employee = get_object_or_404(Employee, sl=emp_id)
    profile = get_object_or_404(EmployeeProfile, employee=employee)
    today = date.today()

    if request.method == "POST":
        if "clock_in" in request.POST or "clock_out" in request.POST:
            if not is_office_ip(request):
                messages.error(
                    request,
                    "Attendance can only be marked from the office network.",
                )
                return redirect("dashboard")

            now = timezone.localtime(timezone.now()).time()
            window_error = attendance_window_error(now)
            if window_error:
                messages.error(request, window_error)
                return redirect("dashboard")

            today_att = profile.attendances.filter(date=today).first()

            if "clock_in" in request.POST:
                if today_att:
                    messages.error(
                        request, "Today's attendance has already been recorded."
                    )
                    return redirect("dashboard")
                Attendance.objects.create(
                    employee=profile,
                    date=today,
                    check_in=now,
                    status=attendance_status_for(now),
                )
                messages.success(request, "Checked in successfully.")
                return redirect("dashboard")

            if "clock_out" in request.POST:
                if not today_att:
                    messages.error(request, "Please check in before checking out.")
                    return redirect("dashboard")
                if today_att.check_out:
                    messages.error(
                        request, "Today's attendance has already been recorded."
                    )
                    return redirect("dashboard")
                today_att.check_out = now
                today_att.save()
                messages.success(request, "Checked out successfully.")
                return redirect("dashboard")

    today_attendance = profile.attendances.filter(date=today).first()

    all_profiles = EmployeeProfile.objects.select_related("employee").all()
    today_records = Attendance.objects.filter(date=today)
    attended_ids = set(today_records.values_list("employee_id", flat=True))
    present_count = today_records.filter(status="Present").count()
    late_count = today_records.filter(status="Late").count()
    absent_count = sum(1 for p in all_profiles if p.id not in attended_ids)

    pending_leave_count = Leave.objects.filter(
        employee=profile, status='Pending'
    ).count()

    last_attendances = profile.attendances.order_by("-date")[:5]

    context = {
        "profile": profile,
        "last_attendances": last_attendances,
        "today": today,
        "today_attendance": today_attendance,
        "working_hours": format_working_hours_long(
            today_attendance.check_in if today_attendance else None,
            today_attendance.check_out if today_attendance else None,
        ),
        "client_ip": get_client_ip(request),
        "attendance_summary": {
            "present": present_count,
            "late": late_count,
            "absent": absent_count,
        },
        "pending_leave_count": pending_leave_count,
        "announcements": Announcement.objects.all()[:5],
        "joining_date": profile.user.date_joined.date() if profile.user_id else today,
        "today_production": profile.productions.filter(date=today).first(),
        "production_quantity_today": profile.productions.filter(
            date=today
        ).aggregate(total=Sum("quantity"))["total"] or 0,
        "production_last_entries": profile.productions.order_by("-date")[:5],
    }
    return render(request, "dashboard.html", context)


# ============================================================
# EMPLOYEE - PRODUCTION MODULE
# ============================================================
@employee_required
def employee_production(request):
    """Employee: record daily production for a product and view history."""
    emp_id = request.session.get("employee_id")
    profile = get_object_or_404(EmployeeProfile, employee_id=emp_id)
    today = date.today()

    if request.method == "POST":
        form = ProductionForm(request.POST)
        if form.is_valid():
            production = form.save(commit=False)
            production.employee = profile.employee
            production.employee_profile = profile
            production.date = today
            try:
                production.save()
                messages.success(
                    request,
                    f"Production recorded — {production.quantity} unit(s) of '{production.product.name}' added to stock.",
                )
            except IntegrityError:
                messages.error(
                    request,
                    "Production for this product has already been recorded today.",
                )
            return redirect("employee_production")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
    else:
        form = ProductionForm()

    today_record = profile.productions.filter(date=today).first()
    history = profile.productions.select_related("product").order_by("-date", "-pk")

    return render(request, "production.html", {
        "form": form,
        "today_record": today_record,
        "history": history,
        "today": today,
    })


@employee_required
def employee_production_delete(request, pk):
    """Employee: delete today's own production record (stock is reversed)."""
    emp_id = request.session.get("employee_id")
    production = get_object_or_404(Production, pk=pk, employee_id=emp_id, date=date.today())
    production.delete()
    messages.success(request, "Production record deleted; stock adjusted.")
    return redirect("employee_production")


@csrf_exempt
def payment_success(request):
    tran_id = request.POST.get("tran_id") or request.GET.get("tran_id")

    payment = PaymentTransaction.objects.filter(order_id=tran_id).first()

    if payment:
        if payment.status != "success":
            payment.status = "success"
            payment.save()

            # If customer purchase, create orders and decrease stock atomically
            if payment.customer:
                meta_cart_ids = (payment.metadata or {}).get("cart_item_id") or []
                cart_items = Cart.objects.filter(
                    customer=payment.customer, id__in=meta_cart_ids
                ).select_related("product")
                if not cart_items:
                    cart_items = Cart.objects.filter(
                        customer=payment.customer
                    ).select_related("product")
                if cart_items.exists():
                    product_ids = [ci.product.sl for ci in cart_items]
                    with transaction.atomic():
                        products_locked = Product.objects.select_for_update().filter(sl__in=product_ids)
                        product_map = {p.sl: p for p in products_locked}

                        for item in cart_items:
                            locked_product = product_map.get(item.product.sl)
                            if locked_product and locked_product.stock >= item.quantity:
                                Order.objects.create(
                                    customer=payment.customer,
                                    product=item.product,
                                    quantity=item.quantity,
                                    total_amount=item.subtotal,
                                    payment_method="SSLCommerz",
                                    payment_status="Paid",
                                    shipping_address=request.session.get("shipping_address", ""),
                                    phone=request.session.get("phone", ""),
                                    status="Paid",
                                    color=item.color,
                                    size=item.size,
                                    textile=item.textile,
                                    unit_price=item.price,
                                )
                                if item.color or item.size or item.textile:
                                    variant = ProductVariant.objects.filter(
                                        product=item.product,
                                        color=item.color,
                                        size=item.size,
                                        textile=item.textile,
                                    ).first()
                                    if variant:
                                        previous_variant_stock = variant.stock
                                        variant.stock -= item.quantity
                                        variant.save()
                                        log_inventory(
                                            product=item.product,
                                            transaction_type="decrease",
                                            quantity=item.quantity,
                                            previous_stock=previous_variant_stock,
                                            new_stock=variant.stock,
                                            reason=(
                                                f"Paid order ({item.color}/{item.size}/{item.textile}) "
                                                f"by {payment.customer.name}"
                                            ),
                                            performed_by="Customer",
                                        )
                                else:
                                    previous_stock = locked_product.stock
                                    locked_product.stock -= item.quantity
                                    locked_product.save()
                                    log_inventory(
                                        product=locked_product,
                                        transaction_type="decrease",
                                        quantity=item.quantity,
                                        previous_stock=previous_stock,
                                        new_stock=locked_product.stock,
                                        reason=f"Paid order by {payment.customer.name}",
                                        performed_by="Customer",
                                    )
                        cart_items.delete()

                # Also handle single-item buy_product orders
                existing_orders = Order.objects.filter(
                    customer=payment.customer, payment_status="Pending", status="Pending"
                )
                for order in existing_orders:
                    order.payment_status = "Paid"
                    order.status = "Paid"
                    order.save()

    return render(request, "success.html", {"payment": payment})


@csrf_exempt
def payment_fail(request):
    tran_id = request.POST.get("tran_id")

    payment = PaymentTransaction.objects.filter(order_id=tran_id).first()

    if payment:
        payment.status = "failed"
        payment.save()

    return render(request, "fail.html", {"payment": payment})


# --------------------------
# Employee dashboard
# --------------------------
def home(request):
    if request.session.get("employee_id"):
        return redirect("dashboard")
    return redirect("index")


def logout_view(request):
    request.session.pop("employee_id", None)
    return redirect("login_page")


def format_working_hours_long(check_in_time, check_out_time):
    """Return working duration as 'X Hours Y Minutes' between check-in and check-out."""
    if not check_in_time or not check_out_time:
        return None
    start = timedelta(
        hours=check_in_time.hour, minutes=check_in_time.minute, seconds=check_in_time.second
    )
    end = timedelta(
        hours=check_out_time.hour, minutes=check_out_time.minute, seconds=check_out_time.second
    )
    diff = end - start
    if diff < timedelta(0):
        return None
    total_secs = int(diff.total_seconds())
    hours, minutes = total_secs // 3600, (total_secs % 3600) // 60
    if hours and minutes:
        return f"{hours} Hours {minutes} Minutes"
    if hours:
        return f"{hours} Hours"
    return f"{minutes} Minutes"


def profile_view(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login_page")
    profile = get_object_or_404(EmployeeProfile, employee_id=emp_id)
    return render(request, "profile.html", {"profile": profile})


# ============================================================
# ANNOUNCEMENTS - ADMIN CRUD
# ============================================================
@login_required(login_url="admin_login")
def announcement_list(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    announcements = Announcement.objects.all()
    return render(request, "announcement_list.html", {"announcements": announcements})


@login_required(login_url="admin_login")
def announcement_add(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        if not title or not content:
            messages.error(request, "Title and content are required.")
            return render(request, "announcement_form.html", {"announcement": None})
        Announcement.objects.create(
            title=title, content=content, created_by=request.user
        )
        messages.success(request, "Announcement published.")
        return redirect("announcement_list")
    return render(request, "announcement_form.html", {"announcement": None})


@login_required(login_url="admin_login")
def announcement_edit(request, pk):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        if not title or not content:
            messages.error(request, "Title and content are required.")
            return render(request, "announcement_form.html", {"announcement": announcement})
        announcement.title = title
        announcement.content = content
        announcement.save()
        messages.success(request, "Announcement updated.")
        return redirect("announcement_list")
    return render(request, "announcement_form.html", {"announcement": announcement})


@login_required(login_url="admin_login")
def announcement_delete(request, pk):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.delete()
    messages.success(request, "Announcement deleted.")
    return redirect("announcement_list")


def attendance_history(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login_page")
    profile = get_object_or_404(EmployeeProfile, employee_id=emp_id)
    attendances = profile.attendances.order_by("-date")
    return render(request, "attendance_history.html", {"attendances": attendances})



# --------------------------
# Admin Dashboard PDF Download
# --------------------------
@login_required(login_url="admin_login")
def download_admin_dashboard_pdf(request):
    """Generate and download admin dashboard as PDF"""
    if request.user.is_authenticated and request.user.is_staff:
        # Prepare dashboard data and rendered HTML (always available as a fallback)
        employees = Employee.objects.annotate(
            total_production=Sum("production__quantity")
        )
        products = Product.objects.all()

        # Determine payment status for current month
        current_date = timezone.now()
        month_start = current_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)

        paid_employee_ids = (
            PaymentTransaction.objects.filter(
                employee__isnull=False,
                status="success",
                created_at__gte=month_start,
                created_at__lt=month_end,
            )
            .values_list("employee_id", flat=True)
            .distinct()
        )

        # Attach payment_status attribute for template rendering
        for emp in employees:
            emp.payment_status = "Paid" if emp.sl in paid_employee_ids else "Unpaid"

        # Render HTML template (available even if PDF generation fails)
        html_content = render_to_string(
            "admin_dashboard_pdf.html",
            {
                "employees": employees,
                "products": products,
                "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        # Now attempt PDF generation if the library is available
        try:
            # Import xhtml2pdf locally to ensure it's available
            from xhtml2pdf import pisa as pisa_module

            # Generate PDF using xhtml2pdf (pass bytes when possible)
            pdf_buffer = BytesIO()
            try:
                # Try passing encoded bytes (more reliable for encodings)
                pisa_status = pisa_module.CreatePDF(
                    html_content.encode("utf-8"), dest=pdf_buffer, encoding="UTF-8"
                )
            except TypeError:
                # Fallback: some environments expect a string source
                pisa_status = pisa_module.CreatePDF(
                    html_content, dest=pdf_buffer, encoding="UTF-8"
                )

            if pisa_status.err:
                # If PDF generation failed, fall back to returning the rendered HTML
                fallback_name = "admin_dashboard_{}.html".format(
                    datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                response = HttpResponse(
                    html_content, content_type="text/html; charset=utf-8"
                )
                response["Content-Disposition"] = 'attachment; filename="{}"'.format(
                    fallback_name
                )
                return response

            pdf_buffer.seek(0)

            # Create HTTP response
            response = HttpResponse(
                pdf_buffer.getvalue(), content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                'attachment; filename="admin_dashboard_{}.pdf"'.format(
                    datetime.now().strftime("%Y%m%d_%H%M%S")
                )
            )

            return response

        except ModuleNotFoundError as e:
            error_msg = "PDF generation library (xhtml2pdf) not installed: " + str(e)
            import traceback

            tb = traceback.format_exc()
            # log to file for easier debugging
            with open("pdf_errors.log", "a", encoding="utf-8") as _f:
                _f.write(
                    "\n==== ModuleNotFoundError at {} ====".format(
                        datetime.now().isoformat()
                    )
                )
                _f.write("\n" + error_msg + "\n")
                _f.write(tb + "\n")
            # Return the rendered HTML as fallback attachment so the admin can still download the content
            fallback_name = "admin_dashboard_{}.html".format(
                datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            response = HttpResponse(
                html_content, content_type="text/html; charset=utf-8"
            )
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(
                fallback_name
            )
            return response

        except Exception as e:
            error_msg = "PDF generation error: " + str(e)
            import traceback

            tb = traceback.format_exc()
            # log the full traceback to a file for inspection
            with open("pdf_errors.log", "a", encoding="utf-8") as _f:
                _f.write(
                    "\n==== PDF generation Exception at {} ====".format(
                        datetime.now().isoformat()
                    )
                )
                _f.write("\n" + error_msg + "\n")
                _f.write(tb + "\n")
            # Return a concise message to the browser
            return HttpResponse(
                "PDF generation failed. See pdf_errors.log for details.", status=500
            )

    return redirect("admin_login")


# --------------------------
# Employee Rating
# --------------------------
@login_required(login_url="admin_login")
def update_employee_rating(request, employee_id):
    """Update employee rating via AJAX"""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse("Unauthorized", status=401)

    if request.method == "POST":
        import json

        try:
            data = json.loads(request.body)
            rating = data.get("rating")

            # Validate rating
            valid_ratings = ["Excellent", "Good", "Average", "Poor"]
            if rating not in valid_ratings:
                return HttpResponse(
                    json.dumps({"error": "Invalid rating"}),
                    content_type="application/json",
                    status=400,
                )

            # Update employee
            employee = get_object_or_404(Employee, sl=employee_id)
            employee.rating = rating
            employee.save()

            return HttpResponse(
                json.dumps({"success": True, "rating": rating}),
                content_type="application/json",
            )
        except Exception as e:
            return HttpResponse(
                json.dumps({"error": str(e)}),
                content_type="application/json",
                status=500,
            )

    return HttpResponse("Method not allowed", status=405)


# --------------------------
# Payment integration (SSLCommerz) - generic flow for employee
# --------------------------
@login_required(login_url="admin_login")
def initiate_payment(request):
    # Check if user is staff (admin)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    if not request.user.is_staff:
        return JsonResponse({"error": "Insufficient permissions"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    target_type = request.POST.get("target_type", "").strip()
    target_id = request.POST.get("target_id", "").strip()
    amount = request.POST.get("amount", "").strip()

    # Validate inputs
    if not target_type:
        return JsonResponse({"error": "Missing target_type parameter"}, status=400)
    if not target_id:
        return JsonResponse({"error": "Missing target_id parameter"}, status=400)
    if not amount:
        return JsonResponse({"error": "Missing amount parameter"}, status=400)

    employee = None

    try:
        target_id = int(target_id)  # Convert to int for database lookup

        if target_type == "employee":
            employee = get_object_or_404(Employee, sl=target_id)
            default_amount = employee.salary
        else:
            return JsonResponse(
                {"error": f"Invalid target_type: {target_type}"}, status=400
            )
    except ValueError:
        return JsonResponse({"error": "target_id must be a valid integer"}, status=400)
    except Http404:
        return JsonResponse(
            {"error": f"{target_type.capitalize()} with id {target_id} not found"},
            status=404,
        )
    except Exception as e:
        return JsonResponse({"error": f"Error finding target: {str(e)}"}, status=500)

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            return JsonResponse({"error": "Amount must be greater than 0"}, status=400)
    except ValueError:
        return JsonResponse({"error": f"Invalid amount value: {amount}"}, status=400)

    # Create order id
    order_id = f"PAY-{target_type[:3].upper()}-{uuid.uuid4().hex[:10]}"

    # Create PaymentTransaction record
    from .models import PaymentTransaction

    try:
        txn = PaymentTransaction.objects.create(
            order_id=order_id,
            employee=employee,
            amount=amount_val,
            currency="BDT",
            status="pending",
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to create transaction: {str(e)}"}, status=500
        )

    # Check settings
    store_id = getattr(settings, "SSL_COMMERZ_STORE_ID", None)
    store_pass = getattr(settings, "SSL_COMMERZ_STORE_PASSWORD", None)
    if not store_id or not store_pass:
        txn.status = "failed"
        txn.metadata = {"error": "missing_store_credentials"}
        txn.save()
        return JsonResponse(
            {
                "error": "Payment credentials not configured. Please contact administrator."
            },
            status=500,
        )

    # Prepare payload for SSLCommerz (sandbox endpoint)
    try:
        success_url = request.build_absolute_uri(reverse("ssl_success"))
        fail_url = request.build_absolute_uri(reverse("ssl_fail"))
        cancel_url = request.build_absolute_uri(reverse("ssl_fail"))
    except Exception as e:
        return JsonResponse({"error": f"Failed to build URLs: {str(e)}"}, status=500)

    payload = {
        "store_id": store_id,
        "store_passwd": store_pass,
        "total_amount": str(amount_val),
        "currency": "BDT",
        "tran_id": order_id,
        "success_url": success_url,
        "fail_url": fail_url,
        "cancel_url": cancel_url,
        "cus_name": (
            employee.name if employee else "Customer"
        ),
        "cus_email": (
            employee.email
            if employee
            else "customer@example.com"
        ),
        "cus_phone": (
            str(employee.phone)
            if employee
            else "0000000000"
        ),
        "cus_add1": "N/A",
        "cus_city": "Dhaka",
        "cus_postcode": "1000",
        "cus_country": "Bangladesh",
        "ship_name": (
            employee.name if employee else "Customer"
        ),
        "ship_add1": "N/A",
        "ship_city": "Dhaka",
        "ship_postcode": "1000",
        "ship_country": "Bangladesh",
        "shipping_method": "NO",
        "product_name": f"Salary Payment - {order_id}",
        "product_category": "topup",  # Required field - using 'topup' for salary/payment transactions
        "product_profile": "general",
        "value_a": str(txn.id),
    }

    try:
        api_url = getattr(
            settings,
            "SSLCOMMERZ_API_URL",
            "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
        )
        resp = requests.post(api_url, data=payload, timeout=15)
        resp.raise_for_status()  # Raise exception for non-200 status codes

        try:
            data = resp.json()
        except ValueError as e:
            import sys

            print(f"JSON Parse Error: {str(e)}", file=sys.stderr)
            print(f"Response text: {resp.text}", file=sys.stderr)
            return JsonResponse(
                {"error": "Invalid JSON response from payment gateway"}, status=500
            )

        # Log the gateway response for debugging
        import sys

        print(f"Gateway response: {data}", file=sys.stderr)

        # Expected: status 'SUCCESS' and 'GatewayPageURL'
        if data.get("status") in ("SUCCESS", "success") and data.get("GatewayPageURL"):
            gateway_url = data["GatewayPageURL"]
            return JsonResponse({"gateway_url": gateway_url, "success": True})
        else:
            txn.status = "failed"
            txn.metadata = data
            txn.save()
            error_msg = data.get("failedreason", data.get("status", "Unknown error"))
            print(f"Gateway error: {error_msg}", file=sys.stderr)
            return JsonResponse(
                {"error": f"Payment gateway error: {error_msg}"}, status=400
            )

    except requests.exceptions.Timeout:
        txn.status = "failed"
        txn.metadata = {"error": "Gateway timeout after 15 seconds"}
        txn.save()
        return JsonResponse(
            {"error": "Payment gateway timed out. Please try again."}, status=500
        )

    except requests.exceptions.ConnectionError as e:
        txn.status = "failed"
        txn.metadata = {"error": f"Connection failed: {str(e)}"}
        txn.save()
        return JsonResponse(
            {
                "error": "Failed to connect to payment gateway. Check your internet connection."
            },
            status=500,
        )

    except requests.exceptions.RequestException as e:
        txn.status = "failed"
        txn.metadata = {"error": str(e)}
        txn.save()
        return JsonResponse(
            {"error": f"Gateway communication error: {str(e)}"}, status=500
        )

    except Exception as e:
        txn.status = "failed"
        txn.metadata = {"error": str(e)}
        txn.save()
        return JsonResponse(
            {"error": f"Payment processing error: {str(e)}"}, status=500
        )


@csrf_exempt
def ssl_success(request):
    # Called after payment success (user redirect)
    tran_id = request.GET.get("tran_id") or request.POST.get("tran_id")
    val_id = request.GET.get("val_id") or request.POST.get("val_id")
    status = request.GET.get("status") or request.POST.get("status")

    from .models import PaymentTransaction

    try:
        txn = PaymentTransaction.objects.get(order_id=tran_id)
    except PaymentTransaction.DoesNotExist:
        return HttpResponse("Unknown transaction", status=404)

    if txn.status != "success":
        txn.status = "success"
        txn.ssl_txn_id = val_id or txn.ssl_txn_id
        txn.metadata = txn.metadata or {}
        txn.metadata.update({"status": status})
        txn.save()

        # send confirmation email if possible
        try:
            recipient = (
                txn.employee.email
                if txn.employee
                else None
            )
            if recipient:
                send_mail(
                    subject="Payment Received",
                    message=f"Payment of {txn.amount} {txn.currency} has been received for order {txn.order_id}.",
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[recipient],
                    fail_silently=True,
                )
        except Exception:
            pass

    messages.success(request, f"Payment processed for {txn.order_id}.")
    return redirect("employee_list")


@csrf_exempt
def ssl_fail(request):
    tran_id = request.GET.get("tran_id") or request.POST.get("tran_id")
    from .models import PaymentTransaction

    try:
        txn = PaymentTransaction.objects.get(order_id=tran_id)
        txn.status = "failed"
        txn.save()
    except PaymentTransaction.DoesNotExist:
        pass
    messages.error(request, "Payment failed or cancelled.")
    return redirect("employee_list")


@csrf_exempt
def ssl_ipn(request):
    # IPN handler - SSLCommerz server-to-server notification
    from .models import PaymentTransaction

    try:
        post = request.POST
        tran_id = post.get("tran_id")
        val_id = post.get("val_id")
        status = post.get("status")

        if not tran_id:
            return HttpResponse("Missing tran_id", status=400)

        txn = PaymentTransaction.objects.filter(order_id=tran_id).first()
        if not txn:
            return HttpResponse("Unknown transaction", status=404)

        if status and status.upper() in ("VALID", "SUCCESS"):
            if txn.status != "success":
                txn.status = "success"
                txn.ssl_txn_id = val_id or txn.ssl_txn_id
                txn.metadata = txn.metadata or {}
                txn.metadata.update({"ipn": dict(post)})
                txn.save()
                # notify recipient
                try:
                    recipient = (
                        txn.employee.email
                        if txn.employee
                        else None
                    )
                    if recipient:
                        send_mail(
                            subject="Payment Confirmed",
                            message=f"Your payment of {txn.amount} {txn.currency} for order {txn.order_id} is confirmed.",
                            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                            recipient_list=[recipient],
                            fail_silently=True,
                        )
                except Exception:
                    pass
        else:
            txn.status = "failed"
            txn.metadata = txn.metadata or {}
            txn.metadata.update({"ipn": dict(post)})
            txn.save()

        return HttpResponse("OK")
    except Exception as e:
        return HttpResponse("Error: " + str(e), status=500)


@login_required(login_url="admin_login")
# ============================================================
# ADMIN - PAY EMPLOYEES & SUPPLIERS
# ============================================================
def admin_pay(request):
    from django.utils import timezone as tz
    from datetime import datetime
    import calendar

    now = tz.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = month_start.month + 1
    next_year = month_start.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_end = month_start.replace(month=next_month, year=next_year)

    employees = Employee.objects.all()

    paid_employee_ids = set(
        PaymentTransaction.objects.filter(
            employee__isnull=False, status="success",
            created_at__gte=month_start, created_at__lt=month_end
        ).values_list("employee_id", flat=True)
    )

    for emp in employees:
        emp.payment_status = "Paid" if emp.sl in paid_employee_ids else "Unpaid"

    context = {
        "employees": employees,
    }
    return render(request, "admin_pay.html", context)


@login_required(login_url="admin_login")
# ============================================================
# ADMIN - PAYMENT TRANSACTIONS
# ============================================================
def payment_transactions_list(request):
    """Admin view: list payment transactions with actions"""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    from .models import PaymentTransaction

    txns = PaymentTransaction.objects.select_related("employee").order_by(
        "-created_at"
    )
    return render(request, "payment_transactions_list.html", {"transactions": txns})


@login_required(login_url="admin_login")
def retry_payment_transaction(request, pk):
    """Admin: retry a failed/cancelled transaction by creating a new transaction and initiating gateway."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse("Unauthorized", status=401)

    from .models import PaymentTransaction

    orig = get_object_or_404(PaymentTransaction, pk=pk)

    # Only allow retry for non-success transactions
    if orig.status == "success":
        messages.info(request, "Transaction already successful; cannot retry.")
        return redirect("payment_transactions_list")

    # create a new transaction and attempt initiation (similar to initiate_payment)
    order_id = f"RETRY-{uuid.uuid4().hex[:10]}"
    txn = PaymentTransaction.objects.create(
        order_id=order_id,
        employee=orig.employee,
        amount=orig.amount,
        currency=orig.currency,
        status="pending",
    )

    store_id = getattr(settings, "SSL_COMMERZ_STORE_ID", None)
    store_pass = getattr(settings, "SSL_COMMERZ_STORE_PASSWORD", None)
    if not store_id or not store_pass:
        txn.status = "failed"
        txn.metadata = {"error": "missing_store_credentials"}
        txn.save()
        messages.error(request, "Payment credentials not configured.")
        return redirect("payment_transactions_list")

    success_url = request.build_absolute_uri(reverse("payment_success"))
    fail_url = request.build_absolute_uri(reverse("payment_fail"))

    payload = {
        "store_id": store_id,
        "store_passwd": store_pass,
        "total_amount": str(txn.amount),
        "currency": txn.currency,
        "tran_id": txn.order_id,
        "success_url": success_url,
        "fail_url": fail_url,
        "cancel_url": fail_url,
        "cus_name": (
            txn.employee.name
            if txn.employee
            else ""
        ),
        "cus_email": (
            txn.employee.email
            if txn.employee
            else ""
        ),
        "cus_phone": (
            txn.employee.phone
            if txn.employee
            else ""
        ),
        "value_a": str(txn.id),
    }

    try:
        api_url = getattr(
            settings,
            "SSLCOMMERZ_API_URL",
            "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
        )
        resp = requests.post(api_url, data=payload, timeout=15)
        data = resp.json()
        if data.get("status") in ("SUCCESS", "success") and data.get("GatewayPageURL"):
            gateway_url = data["GatewayPageURL"]
            return redirect(gateway_url)
        else:
            txn.status = "failed"
            txn.metadata = data
            txn.save()
            messages.error(request, "Retry initiation failed.")
            return redirect("payment_transactions_list")
    except Exception as e:
        txn.status = "failed"
        txn.metadata = {"exception": str(e)}
        txn.save()
        messages.error(request, "Retry error: " + str(e))
        return redirect("payment_transactions_list")


@login_required(login_url="admin_login")
def refund_payment_transaction(request, pk):
    """Admin: mark a transaction as refunded (placeholder for gateway refund API)."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse("Unauthorized", status=401)

    from .models import PaymentTransaction

    txn = get_object_or_404(PaymentTransaction, pk=pk)

    # If already refunded or not successful, still allow marking refunded
    try:
        # Placeholder: if a refund API is available, call it here using settings
        # For now, mark locally as refunded and record metadata
        txn.status = "refunded"
        meta = txn.metadata or {}
        meta.update(
            {"refunded_by": request.user.username, "refunded_at": str(timezone.now())}
        )
        txn.metadata = meta
        txn.save()
        messages.success(request, f"Transaction {txn.order_id} marked as refunded.")
    except Exception as e:
        messages.error(request, "Refund failed: " + str(e))

    return redirect("payment_transactions_list")


@login_required(login_url="admin_login")
def mark_payment_as_paid(request):
    """Admin: mark an employee payment as paid without gateway (manual/off-platform payment)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User not authenticated"}, status=401)

    if not request.user.is_staff:
        return JsonResponse({"error": "Insufficient permissions"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    target_type = request.POST.get("target_type", "").strip()
    target_id = request.POST.get("target_id", "").strip()
    amount = request.POST.get("amount", "").strip()

    if not target_type or not target_id or not amount:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    employee = None

    try:
        target_id = int(target_id)

        if target_type == "employee":
            employee = get_object_or_404(Employee, sl=target_id)
        else:
            return JsonResponse(
                {"error": f"Invalid target_type: {target_type}"}, status=400
            )
    except ValueError:
        return JsonResponse({"error": "target_id must be a valid integer"}, status=400)
    except Http404:
        return JsonResponse(
            {"error": f"{target_type.capitalize()} with id {target_id} not found"},
            status=404,
        )
    except Exception as e:
        return JsonResponse({"error": f"Error finding target: {str(e)}"}, status=500)

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            return JsonResponse({"error": "Amount must be greater than 0"}, status=400)
    except ValueError:
        return JsonResponse({"error": f"Invalid amount value: {amount}"}, status=400)

    # Create order id
    order_id = f"MANUAL-{target_type[:3].upper()}-{uuid.uuid4().hex[:10]}"

    # Create PaymentTransaction record marked as success
    from .models import PaymentTransaction

    try:
        txn = PaymentTransaction.objects.create(
            order_id=order_id,
            employee=employee,
            amount=amount_val,
            currency="BDT",
            status="success",
            metadata={
                "marked_paid_by": request.user.username,
                "marked_at": str(timezone.now()),
                "payment_type": "manual",
            },
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to create payment record: {str(e)}"}, status=500
        )

    # Send confirmation email
    try:
        recipient = (
            employee.email if employee else None
        )
        if recipient:
            send_mail(
                subject="Payment Marked as Paid",
                message=f"Payment of {amount_val} BDT has been marked as paid for order {order_id}.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient],
                fail_silently=True,
            )
    except Exception as e:
        import sys

        print(f"Email sending error (non-blocking): {str(e)}", file=sys.stderr)

    return JsonResponse(
        {
            "success": True,
            "message": "Payment marked as paid successfully",
            "order_id": order_id,
        }
    )


# ============================================================
# BUYER CHECKOUT & ORDERS
# ============================================================
def checkout(request):

    customer_id = request.session.get("customer_id")

    if not customer_id:
        return redirect("customer_login_page")

    customer = Customer.objects.get(id=customer_id)

    # Per-item checkout: cart_id passed as query param (GET) or session
    cart_id = request.GET.get("cart_id") or request.session.get("checkout_cart_id")
    if cart_id:
        request.session["checkout_cart_id"] = cart_id

    if cart_id:
        cart_items = Cart.objects.filter(customer=customer, id=cart_id).select_related("product")
        if not cart_items:
            messages.warning(request, "That cart item is no longer available.")
            return redirect("customer_cart")
        cart_item = cart_items.first()
        total_quantity = cart_item.quantity
    else:
        cart_items = Cart.objects.filter(customer=customer).select_related("product")
        if not cart_items:
            messages.warning(request, "Your cart is empty.")
            return redirect("customer_dashboard")
        total_quantity = sum(item.quantity for item in cart_items)

    # Max 7 items per order
    if total_quantity > 7:
        messages.error(
            request,
            "You can purchase a maximum of 7 items in a single order. Please reduce the quantity before proceeding.",
        )
        return redirect("customer_cart")

    cart_total = sum(item.subtotal for item in cart_items)
    if cart_total <= 0:
        messages.error(request, "Unable to process checkout for zero total amount.")
        return redirect("customer_dashboard")

    if request.method == "POST":

        payment = request.POST.get("payment")

        # ================= CASH ON DELIVERY =================

        if payment == "cod":

            # Atomic stock reservation: lock rows to prevent race conditions
            with transaction.atomic():
                product_ids = [item.product.sl for item in cart_items]
                products_locked = Product.objects.select_for_update().filter(sl__in=product_ids)
                product_map = {p.sl: p for p in products_locked}

                # Verify stock for the single item
                item = cart_items.first()
                if item.color or item.size or item.textile:
                    variant = ProductVariant.objects.select_for_update().filter(
                        product=item.product,
                        color=item.color,
                        size=item.size,
                        textile=item.textile,
                    ).first()
                    available = variant.stock if variant else 0
                    if not variant or variant.stock < item.quantity:
                        messages.error(
                            request,
                            f"Only {available} items are available for this variant.",
                        )
                        return redirect("checkout")
                else:
                    locked_product = product_map[item.product.sl]
                    if locked_product.stock < item.quantity:
                        messages.error(
                            request,
                            f'Sorry, "{locked_product.name}" only has {locked_product.stock} units left. Your order could not be placed.',
                        )
                        return redirect("checkout")

                # Stock validated — create order and deduct
                Order.objects.create(
                    customer=customer,
                    product=item.product,
                    quantity=item.quantity,
                    total_amount=item.subtotal,
                    payment_method="Cash on Delivery",
                    payment_status="Pending",
                    shipping_address=request.POST.get("address1", ""),
                    phone=request.POST.get("phone", ""),
                    status="Pending",
                    color=item.color,
                    size=item.size,
                    textile=item.textile,
                    unit_price=item.price,
                )
                if item.color or item.size or item.textile:
                    variant = ProductVariant.objects.filter(
                        product=item.product,
                        color=item.color,
                        size=item.size,
                        textile=item.textile,
                    ).first()
                    if variant:
                        previous_variant_stock = variant.stock
                        variant.stock -= item.quantity
                        variant.save()
                        log_inventory(
                            product=item.product,
                            transaction_type="decrease",
                            quantity=item.quantity,
                            previous_stock=previous_variant_stock,
                            new_stock=variant.stock,
                            reason=(
                                f"COD order ({item.color}/{item.size}/{item.textile}) "
                                f"by {customer.name}"
                            ),
                            performed_by="Customer",
                        )
                else:
                    locked_product = product_map[item.product.sl]
                    previous_stock = locked_product.stock
                    locked_product.stock -= item.quantity
                    locked_product.save()
                    log_inventory(
                        product=locked_product,
                        transaction_type="decrease",
                        quantity=item.quantity,
                        previous_stock=previous_stock,
                        new_stock=locked_product.stock,
                        reason=f"COD order by {customer.name}",
                        performed_by="Customer",
                    )

            # Only remove the checked-out cart item
            item.delete()
            request.session.pop("checkout_cart_id", None)
            messages.success(request, "Order placed successfully.")
            return redirect("orders_html")

        # ================= SSL PAYMENT =================

        elif payment == "ssl":

            request.session["shipping_address"] = request.POST.get("address1", "")
            request.session["phone"] = request.POST.get("phone", "")

            return redirect("start_ssl_payment")

    return render(
        request,
        "checkout.html",
        {
            "customer": customer,
            "cart_items": cart_items,
            "cart_total": cart_total,
        },
    )


def start_ssl_payment(request):

    customer_id = request.session.get("customer_id")

    customer = Customer.objects.get(id=customer_id)

    cart_id = request.session.get("checkout_cart_id") or request.GET.get("cart_id")
    if cart_id:
        cart_items = Cart.objects.filter(customer=customer, id=cart_id)
    else:
        cart_items = Cart.objects.filter(customer=customer)

    if not cart_items:
        messages.warning(request, "That cart item is no longer available.")
        return redirect("customer_cart")

    total_quantity = sum(i.quantity for i in cart_items)
    if total_quantity > 7:
        messages.error(
            request,
            "You can purchase a maximum of 7 items in a single order. Please reduce the quantity before proceeding.",
        )
        return redirect("checkout")

    total = sum(i.subtotal for i in cart_items)

    tran_id = "ORDER-" + uuid.uuid4().hex[:15]
    PaymentTransaction.objects.create(
        order_id=tran_id,
        customer=customer,
        amount=total,
        currency="BDT",
        status="pending",
        metadata={"cart_item_id": [ci.id for ci in cart_items]},
    )
    payload = {
        "store_id": settings.SSL_COMMERZ_STORE_ID,
        "store_passwd": settings.SSL_COMMERZ_STORE_PASSWORD,
        "total_amount": str(total),
        "currency": "BDT",
        "tran_id": tran_id,
        "success_url": request.build_absolute_uri(reverse("payment_success")),
        "fail_url": request.build_absolute_uri(reverse("payment_fail")),
        "cancel_url": request.build_absolute_uri(reverse("payment_fail")),
        "cus_name": customer.name,
        "cus_email": customer.email,
        "cus_phone": customer.phone,
        "product_name": "Products",
        "product_category": "Fashion",
        "product_profile": "general",
    }
    response = requests.post(
        settings.SSLCOMMERZ_API_URL,
        data=payload,
        timeout=20,
    )

    data = response.json()

    return redirect(data["GatewayPageURL"])


def orders_html(request):
    customer_id = request.session.get("customer_id")

    if not customer_id:
        return redirect("customer_login_page")

    customer = Customer.objects.get(id=customer_id)

    orders = Order.objects.filter(customer=customer).order_by("-created_at")

    return render(
        request,
        "orders.html",
        {
            "customer": customer,
            "orders": orders,
        },
    )


# ============================================================
# LEAVE MANAGEMENT
# ============================================================

LEAVE_ENTITLEMENTS = {
    'Casual': {'entitled': 10, 'label': 'Casual Leave (CL)', 'paid': True},
    'Sick': {'entitled': 14, 'label': 'Sick Leave (SL)', 'paid': True},
    'Earned': {'entitled': None, 'label': 'Earned Leave (EL)', 'paid': True},
    'Festival': {'entitled': 11, 'label': 'Festival Leave', 'paid': True},
    'Maternity': {'entitled': 120, 'label': 'Maternity Leave', 'paid': True, 'female_only': True},
    'LWP': {'entitled': None, 'label': 'Leave Without Pay (LWP)', 'paid': False},
}

# Earned Leave: approximately 1 day per 18 working days (~26 working days/month x 12 / 18 = 17.3)
EARNED_DAYS_PER_YEAR = 17


def get_leave_balance(employee_profile):
    """Leave balance per Bangladesh Labour Law (garments sector) rules.

    - Casual / Sick / Festival: fixed per year, expire every year.
    - Earned: accumulates (carried forward), ~1 day per 18 working days.
    - Maternity: 120 days, female employees only.
    - LWP: unlimited, unpaid.
    """
    year = date.today().year
    year_start = date(year, 1, 1)

    def approved_taken(leave_type, start_from=None):
        qs = Leave.objects.filter(
            employee=employee_profile, leave_type=leave_type, status='Approved'
        )
        if start_from:
            qs = qs.filter(start_date__gte=start_from)
        return sum(l.total_days for l in qs)

    first_leave_date = Leave.objects.filter(employee=employee_profile) \
        .values_list('start_date', flat=True).order_by('start_date').first()
    first_year = (first_leave_date or date(year, 1, 1)).year
    years_worked = max(1, year - first_year + 1)

    balance = {}
    for leave_type, cfg in LEAVE_ENTITLEMENTS.items():
        if cfg.get('female_only') and employee_profile.employee.gender != 'Female':
            continue
        if leave_type == 'Earned':
            entitled = EARNED_DAYS_PER_YEAR * years_worked
            taken = approved_taken('Earned')  # all-time — carries forward
        elif cfg['entitled'] is None:  # LWP — unlimited
            entitled = None
            taken = approved_taken('LWP', year_start)
        else:
            entitled = cfg['entitled']
            taken = approved_taken(leave_type, year_start)
        balance[leave_type] = {
            'label': cfg['label'],
            'entitled': entitled,
            'taken': taken,
            'remaining': None if entitled is None else max(0, entitled - taken),
            'paid': cfg['paid'],
        }
    return balance


@employee_required
def apply_leave(request):
    emp_id = request.session.get("employee_id")
    profile = get_object_or_404(EmployeeProfile, employee_id=emp_id)
    balance = get_leave_balance(profile)
    is_female = profile.employee.gender == 'Female'

    if request.method == "POST":
        form = LeaveForm(request.POST, request.FILES)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = profile
            leave_type = leave.leave_type
            days = leave.total_days

            if leave_type == 'Maternity' and not is_female:
                messages.error(request, "Maternity Leave is only available for female employees.")
                return render(request, "apply_leave.html", {
                    "form": form, "balance": balance, "is_female": is_female,
                })

            if leave_type == 'LWP':
                leave.paid_days = 0
                leave.unpaid_days = days
            else:
                remaining = balance.get(leave_type, {}).get('remaining', 0)
                if days <= remaining:
                    leave.paid_days = days
                    leave.unpaid_days = 0
                else:
                    name = leave_type
                    leave.paid_days = remaining
                    leave.unpaid_days = days - remaining
                    if not request.POST.get("confirm_lwp"):
                        messages.error(
                            request,
                            f"Only {remaining} {name} Leaves are available. "
                            "This leave exceeds your available balance. Extra days will be "
                            "treated as Leave Without Pay and salary will be deducted.",
                        )
                        return render(request, "apply_leave.html", {
                            "form": form, "balance": balance, "is_female": is_female,
                            "excess": True, "excess_days": days - remaining,
                        })
            leave.save()
            messages.success(request, "Leave application submitted successfully.")
            return redirect("leave_history")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
    else:
        form = LeaveForm()

    if not is_female:
        form.fields['leave_type'].choices = [
            c for c in form.fields['leave_type'].choices if c[0] != 'Maternity'
        ]

    return render(request, "apply_leave.html", {
        "form": form,
        "balance": balance,
        "is_female": is_female,
    })


@employee_required
def leave_history(request):
    emp_id = request.session.get("employee_id")
    profile = get_object_or_404(EmployeeProfile, employee_id=emp_id)
    leaves = Leave.objects.filter(employee=profile).order_by("-applied_on")
    balance = get_leave_balance(profile)
    year_deduction = sum(
        l.deduction_amount for l in Leave.objects.filter(
            employee=profile, status='Approved', start_date__year=date.today().year
        )
    )
    return render(request, "leave_history.html", {
        "leaves": leaves,
        "balance": balance,
        "year_deduction": year_deduction,
    })


@login_required(login_url="admin_login")
def admin_leave_list(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    status_filter = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()
    month = request.GET.get("month", "").strip()
    leave_type_filter = request.GET.get("leave_type", "").strip()

    leaves = Leave.objects.select_related("employee__employee").order_by("-applied_on")
    if status_filter:
        leaves = leaves.filter(status=status_filter)
    if q:
        leaves = leaves.filter(employee__employee__name__icontains=q)
    if month:
        try:
            y, m = month.split("-")
            leaves = leaves.filter(start_date__year=int(y), start_date__month=int(m))
        except ValueError:
            pass
    if leave_type_filter:
        leaves = leaves.filter(leave_type=leave_type_filter)

    # Attach current leave balance to each row (cached per employee)
    balance_cache = {}
    for lv in leaves:
        if lv.employee_id not in balance_cache:
            balance_cache[lv.employee_id] = get_leave_balance(lv.employee)
        lv.emp_balance = balance_cache[lv.employee_id]

    return render(request, "admin_leave_list.html", {
        "leaves": leaves,
        "current_filter": status_filter,
        "q": q,
        "month": month,
        "leave_type_filter": leave_type_filter,
        "leave_types": LEAVE_ENTITLEMENTS,
    })


@login_required(login_url="admin_login")
def admin_approve_leave(request, leave_id):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    leave = get_object_or_404(Leave, id=leave_id)
    if request.method == "POST":
        action = request.POST.get("action")
        remarks = request.POST.get("admin_remarks", "")
        if action == "approve":
            leave.status = "Approved"
            leave.approved_by = request.user
            leave.admin_remarks = remarks
            leave.save()  # save() recomputes deduction_amount from unpaid_days
            messages.success(request, f"Leave for {leave.employee.employee.name} approved.")
        elif action == "reject":
            leave.status = "Rejected"
            leave.approved_by = request.user
            leave.admin_remarks = remarks
            leave.save()
            messages.warning(request, f"Leave for {leave.employee.employee.name} rejected.")
        return redirect("admin_leave_list")

    return redirect("admin_leave_list")


@login_required(login_url="admin_login")
def admin_leave_deductions(request):
    """Monthly leave summary / salary deduction report per employee."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    today = date.today()
    month = request.GET.get("month", today.strftime("%Y-%m")).strip()
    q = request.GET.get("q", "").strip()
    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
    except (ValueError, AttributeError):
        y, m = today.year, today.month

    leaves = Leave.objects.filter(
        status='Approved', start_date__year=y, start_date__month=m
    ).select_related("employee__employee")
    if q:
        leaves = leaves.filter(employee__employee__name__icontains=q)

    summary = {}
    total_all = {'total': 0, 'paid': 0, 'unpaid': 0, 'deduction': 0}
    for lv in leaves:
        key = lv.employee_id
        if key not in summary:
            summary[key] = {
                'name': lv.employee.employee.name,
                'public_id': lv.employee.public_id,
                'total': 0, 'paid': 0, 'unpaid': 0, 'deduction': 0,
            }
        summary[key]['total'] += lv.total_days
        summary[key]['paid'] += lv.paid_days
        summary[key]['unpaid'] += lv.unpaid_days
        summary[key]['deduction'] += float(lv.deduction_amount)
        total_all['total'] += lv.total_days
        total_all['paid'] += lv.paid_days
        total_all['unpaid'] += lv.unpaid_days
        total_all['deduction'] += float(lv.deduction_amount)

    rows = sorted(summary.values(), key=lambda r: r['name'])
    return render(request, "admin_leave_deductions.html", {
        "rows": rows,
        "total_all": total_all,
        "month": f"{y:04d}-{m:02d}",
        "q": q,
    })


# ============================================================
# PAYROLL - MONTHLY SALARY CALCULATION & PAYMENT RECORDS
# ============================================================
# Overtime is paid at 2x the hourly rate (Bangladesh Labour Act)
OVERTIME_MULTIPLIER = Decimal('2.00')
WORKING_HOURS_PER_DAY = Decimal('8')
STANDARD_END_TIME = time(17, 0)  # office hours end 05:00 PM


def absence_is_final(day):
    """A working day counts as absent only once it has fully passed.

    Today is only marked absent after the office closes (05:00 PM).
    """
    today = date.today()
    if day < today:
        return True
    if day == today:
        return datetime.now().time() >= STANDARD_END_TIME
    return False


def working_days_in_month(year, month):
    """Count Mon-Fri days in a month (Saturday is a weekly holiday)."""
    days = calendar.monthrange(year, month)[1]
    return sum(
        1 for d in range(1, days + 1)
        if date(year, month, d).weekday() < 5  # 0=Mon ... 4=Fri
    )


def overtime_summary_for(profile, year, month):
    """Sum overtime hours for an employee in a month.

    Overtime counts as time worked after the 05:00 PM office end time.
    """
    total_hours = Decimal('0')
    records = Attendance.objects.filter(
        employee=profile, date__year=year, date__month=month
    ).exclude(check_out__isnull=True)
    for att in records:
        end = timedelta(
            hours=att.check_out.hour, minutes=att.check_out.minute, seconds=att.check_out.second
        )
        standard = timedelta(hours=STANDARD_END_TIME.hour, minutes=STANDARD_END_TIME.minute)
        if end > standard:
            total_hours += Decimal(str(round((end - standard).total_seconds() / 3600, 2)))
    return total_hours


def absent_days_for(profile, year, month):
    """Count unauthorised absence days in a month.

    A working day (Mon-Fri) with no attendance record and no approved
    leave is counted as an absent day.
    """
    days = calendar.monthrange(year, month)[1]
    working_dates = [
        date(year, month, d)
        for d in range(1, days + 1)
        if date(year, month, d).weekday() < 5 and absence_is_final(date(year, month, d))
    ]
    attended = set(
        Attendance.objects.filter(
            employee=profile, date__year=year, date__month=month
        ).values_list("date", flat=True)
    )
    leave_dates = set()
    leaves = Leave.objects.filter(
        employee=profile, status='Approved', start_date__year=year, start_date__month=month
    )
    for lv in leaves:
        d = lv.start_date
        while d <= lv.end_date:
            if d.year == year and d.month == month:
                leave_dates.add(d)
            d += timedelta(days=1)
    return sum(1 for d in working_dates if d not in attended and d not in leave_dates)


def monthly_payroll_for(profile, year, month):
    """ - Basic salary comes from the employee record.
    - Paid leave / LWP days come from approved leaves starting in that month.
    - Leave deduction = (basic / 30) x LWP days, matching the Leave module.
    - Attendance deduction = (basic / working days) x unauthorised absences.
    - Overtime = 2x hourly rate for hours worked after 05:00 PM.
    - Net salary = basic - leave deduction - attendance deduction + overtime
      (never below 0).
    """
    from .models import SalaryPayment

    basic = Decimal(profile.employee.salary or 0)
    leaves = Leave.objects.filter(
        employee=profile, status='Approved', start_date__year=year, start_date__month=month
    )
    paid_days = sum(l.paid_days for l in leaves)
    unpaid_days = sum(l.unpaid_days for l in leaves)
    daily = basic / Decimal(30)
    leave_deduction = (daily * unpaid_days).quantize(Decimal('0.01'))

    working_days = working_days_in_month(year, month)
    absent_days = absent_days_for(profile, year, month)
    daily_rate = (basic / Decimal(max(working_days, 1))).quantize(Decimal('0.01'))
    attendance_deduction = (daily_rate * absent_days).quantize(Decimal('0.01'))

    ot_hours = overtime_summary_for(profile, year, month)
    hourly_rate = (daily / WORKING_HOURS_PER_DAY).quantize(Decimal('0.01'))
    overtime_amount = (ot_hours * hourly_rate * OVERTIME_MULTIPLIER).quantize(Decimal('0.01'))

    net = max(
        basic - leave_deduction - attendance_deduction + overtime_amount,
        Decimal('0'),
    )
    month_key = f"{year:04d}-{month:02d}"
    payment = SalaryPayment.objects.filter(
        employee_profile=profile, salary_month=month_key
    ).first()
    return {
        'profile': profile,
        'month_key': month_key,
        'basic': basic,
        'paid_days': paid_days,
        'unpaid_days': unpaid_days,
        'leave_deduction': leave_deduction,
        'absent_days': absent_days,
        'attendance_deduction': attendance_deduction,
        'overtime_hours': ot_hours,
        'overtime_amount': overtime_amount,
        'total_deduction': (leave_deduction + attendance_deduction).quantize(Decimal('0.01')),
        'net': net.quantize(Decimal('0.01')),
        'paid': payment is not None,
        'payment': payment,
    }


@login_required(login_url="admin_login")
def admin_payroll(request):
    """Monthly salary calculation for every employee with payment status."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    today = date.today()
    month = request.GET.get("month", today.strftime("%Y-%m")).strip()
    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
    except (ValueError, AttributeError):
        y, m = today.year, today.month

    profiles = EmployeeProfile.objects.select_related("employee").all()
    rows = [monthly_payroll_for(p, y, m) for p in profiles]
    totals = {
        'basic': sum(r['basic'] for r in rows),
        'leave_deduction': sum(r['leave_deduction'] for r in rows),
        'attendance_deduction': sum(r['attendance_deduction'] for r in rows),
        'overtime_amount': sum(r['overtime_amount'] for r in rows),
        'net': sum(r['net'] for r in rows),
        'paid': sum(1 for r in rows if r['paid']),
        'total': len(rows),
    }
    return render(request, "admin_payroll.html", {
        "rows": rows,
        "totals": totals,
        "month": f"{y:04d}-{m:02d}",
    })


@login_required(login_url="admin_login")
def pay_salary(request, profile_id):
    """Show salary summary for an employee/month and record the payment."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    profile = get_object_or_404(EmployeeProfile, pk=profile_id)
    today = date.today()
    month = request.GET.get("month", today.strftime("%Y-%m")).strip()
    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
    except (ValueError, AttributeError):
        y, m = today.year, today.month
    month_key = f"{y:04d}-{m:02d}"

    if SalaryPayment.objects.filter(employee_profile=profile, salary_month=month_key).exists():
        messages.info(request, "Salary for this month has already been paid.")
        return redirect("admin_payroll")

    if request.method == "POST":
        try:
            other = Decimal(request.POST.get("other_deduction", "0") or "0")
            bonus = Decimal(request.POST.get("bonus", "0") or "0")
        except Exception:
            other = Decimal("0")
            bonus = Decimal("0")
        if other < 0:
            other = Decimal("0")
        if bonus < 0:
            bonus = Decimal("0")
        method = request.POST.get("payment_method", "Cash")
        if method not in dict(SalaryPayment.PAYMENT_METHOD_CHOICES):
            method = "Cash"

        summary = monthly_payroll_for(profile, y, m)
        final = max(
            summary['basic'] - summary['leave_deduction'] - summary['attendance_deduction']
            - other + bonus + summary['overtime_amount'],
            Decimal('0'),
        )

        now = timezone.localtime()
        SalaryPayment.objects.create(
            employee_profile=profile,
            salary_month=month_key,
            basic_salary=summary['basic'],
            paid_leave=summary['paid_days'],
            lwp=summary['unpaid_days'],
            leave_deduction=summary['leave_deduction'],
            attendance_deduction=summary['attendance_deduction'],
            overtime_hours=summary['overtime_hours'],
            overtime_amount=summary['overtime_amount'],
            other_deduction=other,
            bonus=bonus,
            final_salary=final.quantize(Decimal('0.01')),
            payment_method=method,
            payment_date=now.date(),
            payment_time=now.time(),
            paid_by=request.user.username,
        )
        messages.success(
            request,
            f"Salary for {profile.employee.name} ({month_key}) recorded successfully.",
        )
        return redirect("admin_payroll")

    summary = monthly_payroll_for(profile, y, m)
    return render(request, "pay_salary.html", {
        "summary": summary,
        "month": month_key,
        "methods": SalaryPayment.PAYMENT_METHOD_CHOICES,
    })


@login_required(login_url="admin_login")
def salary_payment_history(request):
    """Admin: view all salary payments, search employee, filter by month."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    month = request.GET.get("month", "").strip()
    q = request.GET.get("q", "").strip()

    payments = SalaryPayment.objects.select_related("employee_profile__employee").all()
    if month:
        payments = payments.filter(salary_month__startswith=month)
    if q:
        payments = payments.filter(
            Q(employee_profile__employee__name__icontains=q)
            | Q(employee_profile__public_id__icontains=q)
        )
    payments = payments.order_by("-salary_month", "-payment_date")

    totals = payments.aggregate(total=Sum("final_salary"), bonus=Sum("bonus"))
    return render(request, "salary_payment_history.html", {
        "payments": payments,
        "q": q,
        "month": month,
        "totals": totals,
    })


@login_required(login_url="admin_login")
def download_salary_report(request, month):
    """Admin: download salary report for a month as CSV."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    import csv

    month = month.strip()
    payments = SalaryPayment.objects.select_related("employee_profile__employee").filter(
        salary_month__startswith=month
    ).order_by("employee_profile__employee__name")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="salary_report_{month}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "Employee Name", "Employee ID", "Salary Month", "Basic Salary",
        "Paid Leave", "Leave Without Pay", "Leave Deduction",
        "Absent Days", "Attendance Deduction",
        "Overtime Hours", "Overtime Amount",
        "Other Deduction", "Bonus", "Final Paid Salary",
        "Payment Method", "Payment Date", "Paid By",
    ])
    for p in payments:
        writer.writerow([
            p.employee_profile.employee.name,
            p.employee_profile.public_id,
            p.salary_month,
            p.basic_salary,
            p.paid_leave,
            p.lwp,
            p.leave_deduction,
            p.attendance_deduction,
            p.overtime_hours,
            p.overtime_amount,
            p.other_deduction,
            p.bonus,
            p.final_salary,
            p.payment_method,
            p.payment_date,
            p.paid_by,
        ])
    return response


def salary_slip(request, payment_id):
    """Printable salary slip (admin or the employee themself)."""
    payment = get_object_or_404(
        SalaryPayment.objects.select_related("employee_profile__employee"), pk=payment_id
    )
    is_staff = request.user.is_authenticated and request.user.is_staff
    emp_id = request.session.get("employee_id")
    if not is_staff and not (
        emp_id and payment.employee_profile.employee_id == emp_id
    ):
        return redirect("login_page")
    return render(request, "salary_slip.html", {"payment": payment})


def employee_salary_history(request):
    """Employee: view their own salary payment history."""
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login_page")
    profile = get_object_or_404(EmployeeProfile, employee_id=emp_id)
    payments = profile.salary_payments.all()
    return render(request, "employee_salary_history.html", {
        "payments": payments,
        "profile": profile,
    })


# ============================================================
# DEPARTMENTS & JOB POSITIONS (ADMIN)
# ============================================================
@login_required(login_url="admin_login")
def department_list(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    departments = Department.objects.annotate(
        employee_count=Count("employees")
    ).order_by("name")
    form = DepartmentForm()
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department added.")
            return redirect("department_list")
    return render(request, "department_list.html", {
        "departments": departments,
        "form": form,
    })


@login_required(login_url="admin_login")
def department_edit(request, pk):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated.")
            return redirect("department_list")
    else:
        form = DepartmentForm(instance=dept)
    return render(request, "department_form.html", {"form": form, "dept": dept})


@login_required(login_url="admin_login")
def department_delete(request, pk):
    if request.user.is_authenticated and request.user.is_staff:
        dept = get_object_or_404(Department, pk=pk)
        dept.delete()
        messages.success(request, "Department deleted.")
    return redirect("department_list")


@login_required(login_url="admin_login")
def job_position_list(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    positions = JobPosition.objects.select_related("department").annotate(
        employee_count=Count("employees")
    ).order_by("department__name", "title")
    form = JobPositionForm()
    if request.method == "POST":
        form = JobPositionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Job position added.")
            return redirect("job_position_list")
    return render(request, "job_position_list.html", {
        "positions": positions,
        "form": form,
    })


@login_required(login_url="admin_login")
def job_position_edit(request, pk):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    pos = get_object_or_404(JobPosition, pk=pk)
    if request.method == "POST":
        form = JobPositionForm(request.POST, instance=pos)
        if form.is_valid():
            form.save()
            messages.success(request, "Job position updated.")
            return redirect("job_position_list")
    else:
        form = JobPositionForm(instance=pos)
    return render(request, "job_position_form.html", {"form": form, "pos": pos})


@login_required(login_url="admin_login")
def job_position_delete(request, pk):
    if request.user.is_authenticated and request.user.is_staff:
        pos = get_object_or_404(JobPosition, pk=pk)
        pos.delete()
        messages.success(request, "Job position deleted.")
    return redirect("job_position_list")


@login_required(login_url="admin_login")
def assign_department_position(request, profile_id):
    """Assign department & job position to an employee profile."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    profile = get_object_or_404(EmployeeProfile, pk=profile_id)
    if request.method == "POST":
        form = EmployeeAssignmentForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Department/position assigned to {profile.employee.name}.",
            )
            return redirect("employee_data")
    else:
        form = EmployeeAssignmentForm(instance=profile)
    return render(request, "employee_assignment.html", {
        "form": form,
        "profile": profile,
    })


# ============================================================
# ATTENDANCE VIEWS & REPORTS (ADMIN)
# ============================================================
@login_required(login_url="admin_login")
def daily_attendance(request):
    """Daily attendance view: every employee with Present/Late/Absent/Leave."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    day = request.GET.get("date", date.today().isoformat())
    try:
        day = date.fromisoformat(day)
    except (ValueError, TypeError):
        day = date.today()

    profiles = list(EmployeeProfile.objects.select_related("employee").all())
    att_map = {
        a.employee_id: a
        for a in Attendance.objects.filter(date=day)
    }
    leave_map = {}
    for lv in Leave.objects.filter(
        status="Approved", start_date__lte=day, end_date__gte=day
    ):
        leave_map.setdefault(lv.employee_id, []).append(lv)

    rows = []
    for p in profiles:
        att = att_map.get(p.id)
        leaves = leave_map.get(p.id, [])
        if att:
            status = att.status
        elif leaves:
            status = "On Leave"
        else:
            status = "Absent"
        rows.append({
            "profile": p,
            "attendance": att,
            "leaves": leaves,
            "status": status,
            "working_hours": format_working_hours(
                att.check_in if att else None,
                att.check_out if att else None,
            ),
        })

    summary = {
        "present": sum(1 for r in rows if r["status"] == "Present"),
        "late": sum(1 for r in rows if r["status"] == "Late"),
        "absent": sum(1 for r in rows if r["status"] == "Absent"),
        "on_leave": sum(1 for r in rows if r["status"] == "On Leave"),
        "total": len(rows),
    }
    return render(request, "daily_attendance.html", {
        "rows": rows,
        "day": day,
        "summary": summary,
    })


@login_required(login_url="admin_login")
def monthly_attendance(request):
    """Monthly attendance grid: employee x day matrix with summary stats."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    today = date.today()
    month = request.GET.get("month", today.strftime("%Y-%m")).strip()
    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
    except (ValueError, AttributeError):
        y, m = today.year, today.month

    num_days = calendar.monthrange(y, m)[1]
    days = [date(y, m, d) for d in range(1, num_days + 1)]

    profiles = list(EmployeeProfile.objects.select_related("employee").all())
    att_map = {}
    for a in Attendance.objects.filter(date__year=y, date__month=m):
        att_map.setdefault(a.employee_id, {})[a.date.day] = a

    leave_map = {}
    for lv in Leave.objects.filter(
        status="Approved", start_date__year=y, start_date__month=m
    ):
        d = lv.start_date
        while d <= lv.end_date:
            if d.year == y and d.month == m:
                leave_map.setdefault(lv.employee_id, set()).add(d.day)
            d += timedelta(days=1)

    rows = []
    total = {"present": 0, "late": 0, "leave": 0, "absent": 0}
    today = date.today()
    for p in profiles:
        row = {"profile": p, "cells": []}
        present = late = leave = absent = 0
        for d in days:
            att = att_map.get(p.id, {}).get(d.day)
            if att:
                if att.status == "Late":
                    late += 1
                    row["cells"].append("L")
                else:
                    present += 1
                    row["cells"].append("P")
            elif d.day in leave_map.get(p.id, set()):
                leave += 1
                row["cells"].append("LV")
            elif not absence_is_final(d):
                row["cells"].append("U")
            elif d.weekday() < 5:
                absent += 1
                row["cells"].append("A")
            else:
                row["cells"].append("H")
        row.update(present=present, late=late, leave=leave, absent=absent)
        expected = present + late + leave + absent
        row["expected"] = expected
        row["percentage"] = round((present + late) / expected * 100, 1) if expected else 0
        rows.append(row)
        total["present"] += present
        total["late"] += late
        total["leave"] += leave
        total["absent"] += absent

    total_expected = total["present"] + total["late"] + total["leave"] + total["absent"]
    total["expected"] = total_expected
    total["percentage"] = round(
        (total["present"] + total["late"]) / total_expected * 100, 1
    ) if total_expected else 0

    return render(request, "monthly_attendance.html", {
        "rows": rows,
        "days": days,
        "month": f"{y:04d}-{m:02d}",
        "summary": total,
    })


@login_required(login_url="admin_login")
def attendance_report(request):
    """Present/Absent status report with date range + attendance percentage."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    today = date.today()
    try:
        from_date = date.fromisoformat(request.GET.get("from", date(today.year, today.month, 1).isoformat()))
    except (ValueError, TypeError):
        from_date = date(today.year, today.month, 1)
    try:
        to_date = date.fromisoformat(request.GET.get("to", today.isoformat()))
    except (ValueError, TypeError):
        to_date = today
    if to_date < from_date:
        from_date, to_date = to_date, from_date
    if to_date > today:
        to_date = today
    q = request.GET.get("q", "").strip()

    profiles = EmployeeProfile.objects.select_related("employee").all()
    if q:
        profiles = profiles.filter(employee__name__icontains=q)

    working_dates = [
        d for d in (from_date + timedelta(n) for n in range((to_date - from_date).days + 1))
        if d.weekday() < 5 and absence_is_final(d)
    ]
    working_set = set(working_dates)

    att_records = Attendance.objects.filter(date__gte=from_date, date__lte=to_date)
    att_map = {}
    for a in att_records:
        att_map.setdefault(a.employee_id, []).append(a)

    leave_map = {}
    for lv in Leave.objects.filter(
        status="Approved", start_date__lte=to_date, end_date__gte=from_date
    ):
        d = max(lv.start_date, from_date)
        end = min(lv.end_date, to_date)
        while d <= end:
            leave_map.setdefault(lv.employee_id, set()).add(d)
            d += timedelta(days=1)

    rows = []
    for p in profiles:
        attended = {a.date for a in att_map.get(p.id, [])}
        present = sum(1 for a in att_map.get(p.id, []) if a.status == "Present" and a.date in working_set)
        late = sum(1 for a in att_map.get(p.id, []) if a.status == "Late" and a.date in working_set)
        leave_days = sum(1 for d in working_dates if d in leave_map.get(p.id, set()))
        absent = sum(
            1 for d in working_dates
            if d not in attended and d not in leave_map.get(p.id, set())
        )
        expected = present + late + leave_days + absent
        rows.append({
            "profile": p,
            "present": present,
            "late": late,
            "leave": leave_days,
            "absent": absent,
            "expected": expected,
            "percentage": round((present + late) / expected * 100, 1) if expected else 0,
        })

    summary = {
        "present": sum(r["present"] for r in rows),
        "late": sum(r["late"] for r in rows),
        "leave": sum(r["leave"] for r in rows),
        "absent": sum(r["absent"] for r in rows),
        "expected": sum(r["expected"] for r in rows),
    }
    summary["percentage"] = round(
        (summary["present"] + summary["late"]) / summary["expected"] * 100, 1
    ) if summary["expected"] else 0

    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_attendance_pdf.html",
            {"rows": rows, "summary": summary, "from_date": from_date, "to_date": to_date, "q": q},
            "attendance_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Employee", "Employee ID", "Present", "Late", "Leave", "Absent", "Expected", "Attendance %"],
            [
                [r["profile"].employee.name, r["profile"].public_id, r["present"], r["late"], r["leave"], r["absent"], r["expected"], r["percentage"]]
                for r in rows
            ],
            "attendance_report",
        )

    return render(request, "attendance_report.html", {
        "rows": rows,
        "summary": summary,
        "from_date": from_date,
        "to_date": to_date,
        "q": q,
    })


@login_required(login_url="admin_login")
def admin_leave_balance(request):
    """Admin: leave balance overview for every employee."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    q = request.GET.get("q", "").strip()
    profiles = EmployeeProfile.objects.select_related("employee").all()
    if q:
        profiles = profiles.filter(employee__name__icontains=q)
    rows = []
    for p in profiles:
        rows.append({"profile": p, "balance": get_leave_balance(p)})
    return render(request, "admin_leave_balance.html", {
        "rows": rows,
        "q": q,
        "leave_types": LEAVE_ENTITLEMENTS,
    })


def admin_employee_history(request, profile_id):
    """Admin: complete history report for one employee (attendance, leave,
    leave balance, salary). Admin-only; only shows the requested employee."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")

    profile = get_object_or_404(
        EmployeeProfile.objects.select_related(
            "employee", "department", "job_position"
        ),
        pk=profile_id,
    )

    attendances = list(profile.attendances.all())  # newest first
    leaves = list(profile.leaves.all().order_by("-start_date"))
    salaries = list(profile.salary_payments.all())  # newest first
    balance = get_leave_balance(profile)

    # --- Summary ---
    present = sum(1 for a in attendances if a.status == "Present")
    late = sum(1 for a in attendances if a.status == "Late")

    # Absence scope: from first recorded activity to today, working days
    # (Mon-Fri) that have fully passed, with no attendance and no approved leave.
    first_activity = None
    if attendances:
        first_activity = attendances[-1].date  # attendances sorted desc
    if leaves:
        ldates = [l.start_date for l in leaves]
        ld = min(ldates)
        first_activity = ld if first_activity is None else min(first_activity, ld)
    if first_activity is None:
        first_activity = None
    absent = 0
    if first_activity:
        attended_dates = {a.date for a in attendances}
        leave_dates = set()
        for lv in leaves:
            if lv.status == "Approved":
                d = lv.start_date
                while d <= lv.end_date:
                    leave_dates.add(d)
                    d += timedelta(days=1)
        cur = first_activity
        today = date.today()
        while cur <= today:
            if (
                cur.weekday() < 5
                and absence_is_final(cur)
                and cur not in attended_dates
                and cur not in leave_dates
            ):
                absent += 1
            cur += timedelta(days=1)

    approved_leave = sum(1 for l in leaves if l.status == "Approved")
    pending_leave = sum(1 for l in leaves if l.status == "Pending")
    rejected_leave = sum(1 for l in leaves if l.status == "Rejected")

    summary = {
        "attendance_total": len(attendances),
        "present": present,
        "late": late,
        "absent": absent,
        "leave_total": len(leaves),
        "approved_leave": approved_leave,
        "pending_leave": pending_leave,
        "rejected_leave": rejected_leave,
        "salary_total": len(salaries),
    }

    return render(request, "admin_employee_history.html", {
        "profile": profile,
        "attendances": attendances,
        "leaves": leaves,
        "salaries": salaries,
        "balance": balance,
        "leave_types": LEAVE_ENTITLEMENTS,
        "summary": summary,
        "print_mode": request.GET.get("print") == "1",
        "generated_at": datetime.now(),
    })



# ============================================================
# INVENTORY / STOCK MANAGEMENT (ADMIN)
# ============================================================
@login_required(login_url="admin_login")
def inventory_list(request):
    """Stock overview: availability, low stock alerts, links to update."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    q = request.GET.get("q", "").strip()
    stock_status = request.GET.get("stock", "").strip()
    products = Product.objects.all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(subcategory__icontains=q))
    if stock_status == "low":
        products = products.filter(stock__lte=F("low_stock_threshold"), stock__gt=0)
    elif stock_status == "out":
        products = products.filter(stock=0)
    elif stock_status == "available":
        products = products.filter(stock__gt=F("low_stock_threshold"))
    products = products.order_by("stock", "name")

    summary = {
        "total": Product.objects.count(),
        "available": Product.objects.filter(stock__gt=F("low_stock_threshold")).count(),
        "low": Product.objects.filter(stock__lte=F("low_stock_threshold"), stock__gt=0).count(),
        "out": Product.objects.filter(stock=0).count(),
    }
    return render(request, "inventory_list.html", {
        "products": products,
        "q": q,
        "stock_status": stock_status,
        "summary": summary,
    })


@login_required(login_url="admin_login")
def stock_update(request, sl):
    """Increase / decrease / adjust stock with an InventoryLog entry."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    product = get_object_or_404(Product, sl=sl)
    if request.method == "POST":
        form = StockUpdateForm(request.POST)
        if form.is_valid():
            ttype = form.cleaned_data["transaction_type"]
            qty = form.cleaned_data["quantity"]
            reason = form.cleaned_data["reason"]
            old = product.stock
            if ttype == "increase":
                product.stock += qty
            elif ttype == "decrease":
                if product.stock < qty:
                    messages.error(
                        request,
                        f"Cannot decrease stock below 0. Current stock: {product.stock}.",
                    )
                    return redirect("stock_update", sl=product.sl)
                product.stock -= qty
            else:  # adjustment - set exact stock
                product.stock = qty
            product.save()
            InventoryLog.objects.create(
                product=product,
                transaction_type=ttype,
                quantity=qty,
                previous_stock=old,
                new_stock=product.stock,
                reason=reason,
                performed_by=request.user.username,
            )
            messages.success(request, f"Stock for '{product.name}' updated to {product.stock}.")
            return redirect("inventory_list")
    else:
        form = StockUpdateForm()
    return render(request, "stock_update.html", {
        "form": form,
        "product": product,
    })


@login_required(login_url="admin_login")
def inventory_history(request):
    """Inventory log history with filters."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    q = request.GET.get("q", "").strip()
    ttype = request.GET.get("type", "").strip()
    logs = InventoryLog.objects.select_related("product").all()
    if q:
        logs = logs.filter(product__name__icontains=q)
    if ttype:
        logs = logs.filter(transaction_type=ttype)
    logs = logs.order_by("-created_at")
    return render(request, "inventory_history.html", {
        "logs": logs,
        "q": q,
        "ttype": ttype,
        "types": InventoryLog.TRANSACTION_TYPES,
    })


# ============================================================
# REPORT HELPERS
# ============================================================
def make_pdf_response(template, context, filename):
    """Render a template to PDF via xhtml2pdf, with HTML fallback."""
    context = dict(context)
    context["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_content = render_to_string(template, context)
    try:
        from xhtml2pdf import pisa as pisa_module
        pdf_buffer = BytesIO()
        try:
            pisa_status = pisa_module.CreatePDF(
                html_content.encode("utf-8"), dest=pdf_buffer, encoding="UTF-8"
            )
        except TypeError:
            pisa_status = pisa_module.CreatePDF(
                html_content, dest=pdf_buffer, encoding="UTF-8"
            )
        if pisa_status.err:
            response = HttpResponse(html_content, content_type="text/html; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="{filename}.html"'
            return response
        pdf_buffer.seek(0)
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
        return response
    except Exception:
        response = HttpResponse(html_content, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}.html"'
        return response


def make_excel_response(headers, rows, filename):
    """Generate an Excel (.xlsx) file from headers + row data."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response


# ============================================================
# REPORTS (ADMIN) - 7 report pages with filter / export
# ============================================================
@login_required(login_url="admin_login")
def report_employee(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    q = request.GET.get("q", "").strip()
    dept = request.GET.get("department", "").strip()
    profiles = EmployeeProfile.objects.select_related(
        "employee", "department", "job_position"
    )
    if q:
        profiles = profiles.filter(
            Q(employee__name__icontains=q)
            | Q(employee__email__icontains=q)
            | Q(public_id__icontains=q)
        )
    if dept:
        profiles = profiles.filter(department_id=dept)

    employees = [p.employee for p in profiles]
    for p in profiles:
        p.employee.employeeprofile = p

    summary = {
        "total": len(employees),
        "departments": len({p.department_id for p in profiles if p.department_id}),
        "monthly_cost": sum(e.salary or 0 for e in employees),
    }
    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_employee_pdf.html",
            {"employees": employees, "q": q, "dept": dept, "summary": summary},
            "employee_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Name", "Employee ID", "Email", "Phone", "Position", "Department", "Job Position", "Salary", "Gender", "Rating"],
            [
                [
                    e.name,
                    e.employeeprofile.public_id if hasattr(e, "employeeprofile") else "",
                    e.email,
                    e.phone,
                    e.position,
                    e.employeeprofile.department.name if hasattr(e, "employeeprofile") and e.employeeprofile.department else "",
                    e.employeeprofile.job_position.title if hasattr(e, "employeeprofile") and e.employeeprofile.job_position else "",
                    e.salary,
                    e.gender,
                    e.rating,
                ]
                for e in employees
            ],
            "employee_report",
        )
    return render(request, "report_employee.html", {
        "employees": employees,
        "q": q,
        "dept": dept,
        "departments": Department.objects.all(),
        "summary": summary,
    })


@login_required(login_url="admin_login")
def report_leave(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    today = date.today()
    month = request.GET.get("month", today.strftime("%Y-%m")).strip()
    status_filter = request.GET.get("status", "").strip()
    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
    except (ValueError, AttributeError):
        y, m = today.year, today.month

    leaves = Leave.objects.select_related("employee__employee").filter(
        start_date__year=y, start_date__month=m
    )
    if status_filter:
        leaves = leaves.filter(status=status_filter)

    summary = {
        "total": leaves.count(),
        "days": sum(l.total_days for l in leaves),
        "deduction": sum(l.deduction_amount for l in leaves),
        "approved": leaves.filter(status="Approved").count(),
        "pending": leaves.filter(status="Pending").count(),
    }
    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_leave_pdf.html",
            {"leaves": leaves, "month": f"{y:04d}-{m:02d}", "status_filter": status_filter, "summary": summary},
            "leave_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Employee", "Employee ID", "Leave Type", "Start", "End", "Days", "Paid", "Unpaid", "Deduction", "Status"],
            [
                [
                    lv.employee.employee.name,
                    lv.employee.public_id,
                    lv.leave_type,
                    lv.start_date,
                    lv.end_date,
                    lv.total_days,
                    lv.paid_days,
                    lv.unpaid_days,
                    float(lv.deduction_amount),
                    lv.status,
                ]
                for lv in leaves
            ],
            "leave_report",
        )
    return render(request, "report_leave.html", {
        "leaves": leaves,
        "month": f"{y:04d}-{m:02d}",
        "status_filter": status_filter,
        "summary": summary,
    })


@login_required(login_url="admin_login")
def report_payroll(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    today = date.today()
    month = request.GET.get("month", today.strftime("%Y-%m")).strip()
    q = request.GET.get("q", "").strip()
    payments = SalaryPayment.objects.select_related("employee_profile__employee").filter(
        salary_month__startswith=month
    )
    if q:
        payments = payments.filter(employee_profile__employee__name__icontains=q)
    payments = payments.order_by("employee_profile__employee__name")

    summary = {
        "basic": sum(p.basic_salary for p in payments),
        "leave_deduction": sum(p.leave_deduction for p in payments),
        "attendance_deduction": sum(p.attendance_deduction for p in payments),
        "overtime": sum(p.overtime_amount for p in payments),
        "final": sum(p.final_salary for p in payments),
        "count": payments.count(),
    }
    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_payroll_pdf.html",
            {"payments": payments, "month": month, "summary": summary, "q": q},
            "payroll_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Employee", "Employee ID", "Basic", "Leave Ded.", "Attn Ded.", "OT Hours", "OT Amount", "Other Ded.", "Bonus", "Final"],
            [
                [
                    p.employee_profile.employee.name,
                    p.employee_profile.public_id,
                    float(p.basic_salary),
                    float(p.leave_deduction),
                    float(p.attendance_deduction),
                    float(p.overtime_hours),
                    float(p.overtime_amount),
                    float(p.other_deduction),
                    float(p.bonus),
                    float(p.final_salary),
                ]
                for p in payments
            ],
            "payroll_report",
        )
    return render(request, "report_payroll.html", {
        "payments": payments,
        "month": month,
        "q": q,
        "summary": summary,
    })


@login_required(login_url="admin_login")
def report_sales(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    today = date.today()
    try:
        from_date = date.fromisoformat(request.GET.get("from", date(today.year, today.month, 1).isoformat()))
    except (ValueError, TypeError):
        from_date = date(today.year, today.month, 1)
    try:
        to_date = date.fromisoformat(request.GET.get("to", today.isoformat()))
    except (ValueError, TypeError):
        to_date = today
    if to_date < from_date:
        from_date, to_date = to_date, from_date
    status_filter = request.GET.get("status", "").strip()

    orders = Order.objects.select_related("customer", "product").filter(
        created_at__date__gte=from_date, created_at__date__lte=to_date
    )
    if status_filter:
        orders = orders.filter(status=status_filter)
    orders = orders.order_by("-created_at")

    summary = {
        "orders": orders.count(),
        "revenue": sum(o.total_amount for o in orders),
        "paid": orders.filter(payment_status="Paid").count(),
        "pending": orders.filter(status="Pending").count(),
        "cancelled": orders.filter(status="Cancelled").count(),
    }
    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_sales_pdf.html",
            {"orders": orders, "from_date": from_date, "to_date": to_date, "status_filter": status_filter, "summary": summary},
            "sales_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Order ID", "Customer", "Product", "Qty", "Total", "Payment", "Status", "Date"],
            [
                [
                    o.id,
                    o.customer.name,
                    o.product.name,
                    o.quantity,
                    float(o.total_amount),
                    o.payment_method,
                    o.status,
                    o.created_at.strftime("%Y-%m-%d"),
                ]
                for o in orders
            ],
            "sales_report",
        )
    return render(request, "report_sales.html", {
        "orders": orders,
        "from_date": from_date,
        "to_date": to_date,
        "status_filter": status_filter,
        "summary": summary,
        "statuses": Order.STATUS_CHOICES,
    })


@login_required(login_url="admin_login")
def report_inventory(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    q = request.GET.get("q", "").strip()
    stock_status = request.GET.get("stock", "").strip()
    products = Product.objects.all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(subcategory__icontains=q))
    if stock_status == "low":
        products = products.filter(stock__lte=F("low_stock_threshold"), stock__gt=0)
    elif stock_status == "out":
        products = products.filter(stock=0)
    elif stock_status == "available":
        products = products.filter(stock__gt=F("low_stock_threshold"))
    products = products.order_by("stock")

    summary = {
        "total": products.count(),
        "units": sum(p.stock for p in products),
        "value": sum(p.stock * p.price for p in products),
        "low": sum(1 for p in products if p.is_low_stock and not p.is_out_of_stock),
        "out": sum(1 for p in products if p.is_out_of_stock),
    }
    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_inventory_pdf.html",
            {"products": products, "q": q, "stock_status": stock_status, "summary": summary},
            "inventory_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Product", "Category", "Subcategory", "Price", "Stock", "Threshold", "Status"],
            [
                [
                    p.name,
                    p.category,
                    p.subcategory,
                    float(p.price),
                    p.stock,
                    p.low_stock_threshold,
                    "Out of stock" if p.is_out_of_stock else ("Low" if p.is_low_stock else "Available"),
                ]
                for p in products
            ],
            "inventory_report",
        )
    return render(request, "report_inventory.html", {
        "products": products,
        "q": q,
        "stock_status": stock_status,
        "summary": summary,
    })


@login_required(login_url="admin_login")
def report_orders(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return redirect("admin_login")
    today = date.today()
    try:
        from_date = date.fromisoformat(request.GET.get("from", date(today.year, today.month, 1).isoformat()))
    except (ValueError, TypeError):
        from_date = date(today.year, today.month, 1)
    try:
        to_date = date.fromisoformat(request.GET.get("to", today.isoformat()))
    except (ValueError, TypeError):
        to_date = today
    if to_date < from_date:
        from_date, to_date = to_date, from_date
    status_filter = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()

    orders = Order.objects.select_related("customer", "product").filter(
        created_at__date__gte=from_date, created_at__date__lte=to_date
    )
    if status_filter:
        orders = orders.filter(status=status_filter)
    if q:
        orders = orders.filter(
            Q(customer__name__icontains=q) | Q(product__name__icontains=q)
        )
    orders = orders.order_by("-created_at")

    by_status = {}
    for st, _label in Order.STATUS_CHOICES:
        subset = [o for o in orders if o.status == st]
        by_status[st] = {"count": len(subset), "total": sum(o.total_amount for o in subset)}
    summary = {
        "total": orders.count(),
        "revenue": sum(o.total_amount for o in orders),
        "items": sum(o.quantity for o in orders),
        "avg": round(sum(o.total_amount for o in orders) / orders.count(), 2) if orders.count() else 0,
    }
    export = request.GET.get("export", "")
    if export == "pdf":
        return make_pdf_response(
            "report_orders_pdf.html",
            {"orders": orders, "from_date": from_date, "to_date": to_date, "status_filter": status_filter, "summary": summary},
            "orders_report",
        )
    if export == "excel":
        return make_excel_response(
            ["Order ID", "Customer", "Phone", "Product", "Qty", "Unit Price", "Total", "Payment", "Status", "Date"],
            [
                [
                    o.id,
                    o.customer.name,
                    o.customer.phone,
                    o.product.name,
                    o.quantity,
                    float(o.unit_price) if o.unit_price is not None else "",
                    float(o.total_amount),
                    o.payment_method,
                    o.status,
                    o.created_at.strftime("%Y-%m-%d"),
                ]
                for o in orders
            ],
            "orders_report",
        )
    return render(request, "report_orders.html", {
        "orders": orders,
        "from_date": from_date,
        "to_date": to_date,
        "status_filter": status_filter,
        "q": q,
        "summary": summary,
        "by_status": by_status,
        "statuses": Order.STATUS_CHOICES,
    })
