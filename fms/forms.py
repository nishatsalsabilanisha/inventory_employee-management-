import re
from datetime import date
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Product,
    Production,
    Attendance,
    Customer,
    Order,
    Leave,
    OfficeIP,
    Department,
    JobPosition,
    EmployeeProfile,
    InventoryLog,
)


EMAIL_RE = re.compile(
    r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$'
)


def validate_email_format(email):
    if not EMAIL_RE.match(email):
        return "Enter a valid email address (e.g. user@example.com)."
    return None


def email_already_exists(email):
    from .models import Employee, Customer
    if Employee.objects.filter(email=email).exists():
        return "An employee with this email already exists."
    if Customer.objects.filter(email=email).exists():
        return "A customer with this email already exists."
    if User.objects.filter(email=email).exists():
        return "An admin account with this email already exists."
    return None


def validate_strong_password(password):
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number.")
    if not re.search(r'[!@#\$%^&*(),.?"":{}|<>_\-]', password):
        errors.append("Password must contain at least one special character.")
    return errors


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']


class ProductionForm(forms.ModelForm):
    """Employee daily production entry — product + quantity produced."""

    class Meta:
        model = Production
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Units produced'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.all().order_by('name')
        self.fields['product'].label = "Product"
        self.fields['quantity'].label = "Quantity Produced"

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return qty


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock', 'description', 'image']


class AttendanceEditForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['status', 'check_in', 'check_out']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class OfficeIPForm(forms.ModelForm):
    class Meta:
        model = OfficeIP
        fields = ['ip_address', 'label', 'is_active']
        widgets = {
            'ip_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 192.168.0.100'}),
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Office LAN'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BonusForm(forms.Form):
    percentage = forms.FloatField(
        label="Bonus Percentage",
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter bonus %'})
    )


class EmployeeRegisterForm(forms.Form):
    name = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"})
    )
    phone = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "Phone Number (11 digits)",
            "pattern": "[0-9]{11}", "minlength": "11", "maxlength": "11",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"})
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        if not re.fullmatch(r'\d{11}', phone):
            raise forms.ValidationError("Phone number must be exactly 11 digits.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        fmt_err = validate_email_format(email)
        if fmt_err:
            raise forms.ValidationError(fmt_err)
        dup_err = email_already_exists(email)
        if dup_err:
            raise forms.ValidationError(dup_err)
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        errors = validate_strong_password(password)
        if errors:
            raise forms.ValidationError(" ".join(errors))
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class CustomerRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password", "autocomplete": "new-password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password", "autocomplete": "new-password"})
    )

    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "address", "password"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name", "autocomplete": "new-password"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address", "autocomplete": "new-password"}),
            "phone": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Phone Number (11 digits)",
                "pattern": "[0-9]{11}", "minlength": "11", "maxlength": "11",
                "autocomplete": "new-password",
            }),
            "address": forms.Textarea(attrs={"class": "form-control", "placeholder": "Address", "rows": 3, "autocomplete": "new-password"}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")
        if not re.fullmatch(r'\d{11}', phone):
            raise forms.ValidationError("Phone number must be exactly 11 digits.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        fmt_err = validate_email_format(email)
        if fmt_err:
            raise forms.ValidationError(fmt_err)
        dup_err = email_already_exists(email)
        if dup_err:
            raise forms.ValidationError(dup_err)
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        errors = validate_strong_password(password)
        if errors:
            raise forms.ValidationError(" ".join(errors))
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class CustomerLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address", "autocomplete": "new-password"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password", "autocomplete": "new-password"})
    )


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter your email address"})
    )


class SetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New Password"})
    )
    confirm_new_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm New Password"})
    )

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        errors = validate_strong_password(password)
        if errors:
            raise forms.ValidationError(" ".join(errors))
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm = cleaned_data.get("confirm_new_password")
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["quantity"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1})
        }


class LeaveForm(forms.ModelForm):
    medical_certificate = forms.FileField(
        required=False,
        label="Medical Certificate (optional, for Sick Leave)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*,.pdf"}),
    )

    class Meta:
        model = Leave
        fields = ["leave_type", "start_date", "end_date", "reason", "medical_certificate"]
        widgets = {
            "leave_type": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for leave (optional)"}),
        }

    def clean_start_date(self):
        start = self.cleaned_data.get("start_date")
        if start and start < date.today():
            raise forms.ValidationError("You cannot apply for leave previous months.")
        return start

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date cannot be before start date.")
        return cleaned_data


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Sewing"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description (optional)"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class JobPositionForm(forms.ModelForm):
    class Meta:
        model = JobPosition
        fields = ["title", "department", "description", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Sewing Operator"}),
            "department": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description (optional)"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)


class EmployeeAssignmentForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ["department", "job_position"]
        widgets = {
            "department": forms.Select(attrs={"class": "form-control"}),
            "job_position": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["job_position"].queryset = JobPosition.objects.filter(is_active=True)


class StockUpdateForm(forms.Form):
    TRANSACTION_TYPES = InventoryLog.TRANSACTION_TYPES

    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_TYPES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason (optional)"}),
    )