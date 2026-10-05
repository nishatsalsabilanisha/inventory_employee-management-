from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import uuid
import os
from fms.settings import BASE_DIR

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

class Employee(models.Model):
    RATING_CHOICES = [
        ('Excellent', 'Excellent'),
        ('Good', 'Good'),
        ('Average', 'Average'),
        ('Poor', 'Poor'),
    ]
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    sl=models.AutoField(primary_key=True,auto_created=True)
    name=models.CharField(max_length=20)
    email=models.EmailField(max_length=254)
    position = models.CharField(max_length=10, default='Worker')  
    phone=models.CharField(max_length=20, blank=True, default="")
    salary = models.IntegerField(default=10000) 
    password = models.CharField(max_length=128, null=True, blank=True)  
    bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rating = models.CharField(max_length=20, choices=RATING_CHOICES, default='', blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    must_change_password = models.BooleanField(default=False)

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Menswear', 'Menswear'),
        ('Womenswear', 'Womenswear'),
        ('Kids', 'Kids'),
        ('Activewear', 'Activewear'),
    ]

    SUBCATEGORY_CHOICES = [
        # Men
        ('Jeans', 'Jeans'),
        ('Shirt', 'Shirt'),
        ('Men Shoes', 'Men Shoes'),
        ('T-Shirts', 'T-Shirts'),
        ('Pants', 'Pants'),
        ('Jackets', 'Jackets'),
        # Women
        ('Tops', 'Tops'),
        ('Kamiz', 'Kamiz'),
        ('Salwar Kameez', 'Salwar Kameez'),
        ('Kurti', 'Kurti'),
        ('Dupatta', 'Dupatta'),
        ('Women Shoes', 'Women Shoes'),
        ('Dresses', 'Dresses'),
        ('Skirts', 'Skirts'),
        ('Bags', 'Bags'),
        # Kids
        ('Kids T-Shirts', 'Kids T-Shirts'),
        ('Kids Jeans', 'Kids Jeans'),
        ('Kids Shoes', 'Kids Shoes'),
        ('Kids Dresses', 'Kids Dresses'),
        # General
        ('Accessories', 'Accessories'),
        ('Sports Bra', 'Sports Bra'),
        ('Leggings', 'Leggings'),
        ('Track Pants', 'Track Pants'),
        ('Shorts', 'Shorts'),
    ]

    sl = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, default="")
    sku = models.CharField(max_length=50, blank=True, default="", unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='Menswear'
    )
    subcategory = models.CharField(
        max_length=30,
        choices=SUBCATEGORY_CHOICES,
        default='T-Shirts'
    )

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.stock <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.stock <= 0

    @property
    def status(self):
        return "Out of Stock" if self.stock <= 0 else "Available"

    @property
    def effective_price(self):
        if self.discount_price is not None and 0 <= self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def discount_percent(self):
        if self.discount_price is not None and 0 <= self.discount_price < self.price:
            return int(round((1 - float(self.discount_price) / float(self.price)) * 100))
        return 0

    @property
    def primary_image(self):
        first = self.images.filter(is_primary=True).first()
        if first:
            return first
        return self.images.first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "id"]

    def __str__(self):
        return f"{self.product.name} image #{self.pk}"


class ProductColor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="colors")
    name = models.CharField(max_length=40)

    class Meta:
        unique_together = ("product", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sizes")
    name = models.CharField(max_length=20)

    class Meta:
        unique_together = ("product", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductTextile(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="textiles")
    name = models.CharField(max_length=40)

    class Meta:
        unique_together = ("product", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.CharField(max_length=40)
    size = models.CharField(max_length=20)
    textile = models.CharField(max_length=40)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "color", "size", "textile")

    def __str__(self):
        return f"{self.product.name} - {self.color} / {self.size} / {self.textile}"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class JobPosition(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['department__name', 'title']

    def __str__(self):
        return f"{self.title} ({self.department.name})"


class EmployeeProfile(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    public_id = models.CharField(max_length=12, unique=True, editable=False)
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    job_position = models.ForeignKey(JobPosition, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = 'EMP-' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} ({self.public_id})'
    photo = models.ImageField(
    upload_to="employee_photos/",
    blank=True,
    null=True
)
        
class Production(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    employee_profile = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='productions',null=True)
    date = models.DateField(auto_now_add=True)
    quantity = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='productions')
    
    class Meta:
        unique_together = ('employee_profile', 'date', 'product')

    def __str__(self):
        return f"Employee: {self.employee.name}, Date: {self.date}, Quantity: {self.quantity}"

    def save(self, *args, **kwargs):
        """Sync produced quantity into Product stock (delta-based)."""
        is_new = self.pk is None
        old_qty = 0
        old_product_id = None
        if not is_new:
            old = Production.objects.filter(pk=self.pk).first()
            if old:
                old_qty = old.quantity
                old_product_id = old.product_id
        super().save(*args, **kwargs)

        new_product_id = self.product_id
        if new_product_id:
            old_product_id = old_product_id if old_product_id is not None else new_product_id
            previous_stock = None
            with transaction.atomic():
                if old_product_id != new_product_id:
                    # Produced item was moved to a different product
                    if old_product_id:
                        old_product = Product.objects.select_for_update().get(pk=old_product_id)
                        old_product.stock = max(0, old_product.stock - old_qty)
                        old_product.save(update_fields=["stock"])
                        log_inventory(
                            product=old_product,
                            transaction_type="adjustment",
                            quantity=-old_qty,
                            previous_stock=old_product.stock + old_qty,
                            new_stock=old_product.stock,
                            reason=f"Production record #{self.pk} moved away",
                            performed_by="Production",
                        )
                    delta = self.quantity
                else:
                    delta = self.quantity - old_qty
                    if delta == 0 and not is_new:
                        return
                product = Product.objects.select_for_update().get(pk=new_product_id)
                if previous_stock is None:
                    previous_stock = product.stock
                product.stock = max(0, product.stock + delta)
                product.save(update_fields=["stock"])
                if delta:
                    log_inventory(
                        product=product,
                        transaction_type="increase" if delta > 0 else "decrease",
                        quantity=abs(delta),
                        previous_stock=previous_stock,
                        new_stock=product.stock,
                        reason=f"Production record #{self.pk} ({self.employee.name})",
                        performed_by="Production",
                    )

    def delete(self, *args, **kwargs):
            """Reverse stock added by this production record."""
            if self.product_id:
                with transaction.atomic():
                    product = Product.objects.select_for_update().get(pk=self.product_id)
                    product.stock = max(0, product.stock - self.quantity)
                    product.save(update_fields=["stock"])
                    log_inventory(
                        product=product,
                        transaction_type="decrease",
                        quantity=self.quantity,
                        previous_stock=product.stock + self.quantity,
                        new_stock=product.stock,
                        reason=f"Production record #{self.pk} deleted ({self.employee.name})",
                        performed_by="Production",
                    )
            super().delete(*args, **kwargs)

class OfficeIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    label = models.CharField(max_length=100, blank=True, help_text="e.g. Office LAN")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ip_address}{' (' + self.label + ')' if self.label else ''}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Late', 'Late'),
    ]

    employee = models.ForeignKey(EmployeeProfile,
        on_delete=models.CASCADE,
        related_name='attendances',
        null=False)
    date = models.DateField(default=date.today)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')

    class Meta:
        ordering = ['-date']
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.public_id} - {self.date} - {self.status}"

class Customer(models.Model):
    name=models.CharField(max_length=100)
    email=models.EmailField(unique=True)
    phone=models.CharField(max_length=20)
    password=models.CharField(max_length=128)
    address=models.TextField()

    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    photo = models.ImageField(
    upload_to="customer_photos/",
    blank=True,
    null=True
)
    
class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('In Production', 'In Production'),
        ('Sent', 'Sent'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
    ]

    CANCELLATION_POLICY = {
        'Pending': 'customer_direct',
        'Paid': 'admin_approval',
        'In Production': 'blocked',
        'Sent': 'return_only',
        'Delivered': 'final',
        'Cancelled': 'final',
        'Returned': 'final',
    }

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=30,
        default="SSLCommerz"
    )

    payment_status = models.CharField(
        max_length=20,
        default="Pending"
    )

    shipping_address = models.TextField(blank=True)

    phone = models.CharField(max_length=20, blank=True)

    color = models.CharField(max_length=40, blank=True, default="")
    size = models.CharField(max_length=20, blank=True, default="")
    textile = models.CharField(max_length=40, blank=True, default="")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name} - {self.product.name}"

    @property
    def cancellation_rule(self):
        return self.CANCELLATION_POLICY.get(self.status, 'blocked')

    @property
    def can_customer_cancel(self):
        return self.cancellation_rule in ('customer_direct', 'admin_approval')

    @property
    def requires_admin_approval(self):
        return self.cancellation_rule == 'admin_approval'

    @property
    def can_be_returned(self):
        return self.status in ('Sent', 'Delivered')


class CancellationRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='cancellation_requests')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='cancellation_requests')
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cancellation for Order #{self.order.id} - {self.status}"
    
    
    
class Cart(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    color = models.CharField(max_length=40, blank=True, default="")
    size = models.CharField(max_length=20, blank=True, default="")
    textile = models.CharField(max_length=40, blank=True, default="")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    quantity=models.PositiveIntegerField(default=1)

    class Meta:
        unique_together=('customer','product','color','size','textile')

    @property
    def price(self):
        return self.unit_price if self.unit_price is not None else self.product.price

    @property
    def subtotal(self):
        return self.quantity*self.price
    
class PaymentTransaction(models.Model):
    
    order_id = models.CharField(max_length=128, unique=True)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments"
    )

    employee = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    currency = models.CharField(max_length=10, default="BDT")

    status = models.CharField(max_length=20, default="pending")

    ssl_txn_id = models.CharField(max_length=255, blank=True, null=True)

    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
    
class PasswordResetToken(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=20)  # employee, customer, admin
    token = models.CharField(max_length=256, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=1)

    def __str__(self):
        return f"{self.role} - {self.email} - {'Used' if self.is_used else 'Active'}"


class Leave(models.Model):
    LEAVE_TYPES = [
        ('Casual', 'Casual Leave (CL)'),
        ('Sick', 'Sick Leave (SL)'),
        ('Earned', 'Earned Leave (EL)'),
        ('Festival', 'Festival Leave'),
        ('Maternity', 'Maternity Leave'),
        ('LWP', 'Leave Without Pay (LWP)'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.CASCADE, related_name='leaves'
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    medical_certificate = models.FileField(
        upload_to='leave_certificates/', blank=True, null=True
    )
    paid_days = models.PositiveIntegerField(default=0)
    unpaid_days = models.PositiveIntegerField(default=0)
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    admin_remarks = models.TextField(blank=True)

    @property
    def total_days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def is_paid(self):
        return self.leave_type != 'LWP'

    def save(self, *args, **kwargs):
        if self.unpaid_days and self.employee_id:
            monthly_salary = self.employee.employee.salary or 0
            daily_salary = Decimal(monthly_salary) / Decimal(30)
            self.deduction_amount = daily_salary * Decimal(self.unpaid_days)
        else:
            self.deduction_amount = Decimal('0')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee.name} - {self.leave_type} ({self.status})"

class SalaryPayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('bKash', 'bKash'),
        ('Nagad', 'Nagad'),
        ('Rocket', 'Rocket'),
        ('Other', 'Other'),
    ]

    employee_profile = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='salary_payments')
    salary_month = models.CharField(max_length=7, help_text="Salary month in YYYY-MM format")
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    paid_leave = models.PositiveIntegerField(default=0, help_text="Approved paid leave days in the month")
    lwp = models.PositiveIntegerField(default=0, help_text="Leave without pay days in the month")
    leave_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    attendance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Deduction for unauthorised absences")
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Overtime hours worked in the month")
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Overtime pay for the month")
    other_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_date = models.DateField(default=date.today)
    payment_time = models.TimeField(null=True, blank=True)
    paid_by = models.CharField(max_length=30, blank=True, default='', help_text="Admin who recorded the payment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-salary_month', '-payment_date']
        unique_together = ('employee_profile', 'salary_month')

    def __str__(self):
        return f"{self.employee_profile.employee.name} - {self.salary_month} - {self.final_salary}"


class InventoryLog(models.Model):
    TRANSACTION_TYPES = [
        ('increase', 'Increase (Stock In)'),
        ('decrease', 'Decrease (Stock Out)'),
        ('adjustment', 'Manual Adjustment'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reason = models.TextField(blank=True)
    performed_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.transaction_type} - {self.quantity}"


def log_inventory(product, transaction_type, quantity, previous_stock, new_stock, reason, performed_by):
    """Create a consistent InventoryLog entry for a stock change."""
    return InventoryLog.objects.create(
        product=product,
        transaction_type=transaction_type,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=reason,
        performed_by=performed_by or "",
    )
