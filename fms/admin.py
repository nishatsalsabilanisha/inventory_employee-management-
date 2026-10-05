from django.contrib import admin
from .models import Employee, Product, Attendance, EmployeeProfile
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import (
    Employee,
    Product,
    EmployeeProfile,
    Production,
    Attendance,
    Customer,
    Order,
    PaymentTransaction,
    OfficeIP,
    ProductColor,
    ProductSize,
    ProductTextile,
    ProductVariant,
    ProductImage,
    SalaryPayment,
    Announcement,
    Department,
    JobPosition,
    InventoryLog,
)

admin.site.register(Employee)
admin.site.register(Product)
admin.site.register(Production)
admin.site.register(Customer)
admin.site.register(ProductColor)
admin.site.register(ProductSize)
admin.site.register(ProductTextile)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at", "updated_at")
    search_fields = ("title", "content")
    ordering = ("-created_at",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "color", "size", "textile", "price", "stock")
    list_filter = ("color", "size", "textile")
    search_fields = ("product__name",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "created_at")
    list_filter = ("is_primary",)
    search_fields = ("product__name",)


@admin.register(OfficeIP)
class OfficeIPAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "label", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("public_id", "user", "phone", "designation")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "check_in", "check_out", "status")
    list_filter = ("status", "date")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "product",
        "quantity",
        "total_amount",
        "status",
    )

    list_filter = ("status",)

    search_fields = (
        "customer__name",
        "product__name",
    )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "employee",
        "amount",
        "status",
        "created_at",
    )

    list_filter = ("status",)

    search_fields = (
        "order_id",
        "employee__name",
    )


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "employee_profile",
        "salary_month",
        "basic_salary",
        "leave_deduction",
        "attendance_deduction",
        "overtime_amount",
        "bonus",
        "final_salary",
        "payment_method",
        "payment_date",
        "paid_by",
    )
    list_filter = ("salary_month", "payment_method", "payment_date")
    search_fields = (
        "employee_profile__employee__name",
        "employee_profile__public_id",
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "is_active", "created_at")
    list_filter = ("department", "is_active")
    search_fields = ("title", "department__name")


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ("product", "transaction_type", "quantity", "previous_stock", "new_stock", "performed_by", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("product__name", "reason")
