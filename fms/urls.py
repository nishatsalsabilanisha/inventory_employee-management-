from django.contrib import admin
from django.urls import include, path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('admin/login/', views.custom_admin_login, name='admin_login'),
    path('admin/employee-list/', views.admin_redirect, name='employee_list'),
    path('admin-redirect/', views.admin_redirect, name='admin_redirect'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    
    path('about/', views.about, name='about'),
    path('login/', views.login_page, name='login_page'),
    path('employee/change-password/', views.employee_change_password, name='employee_change_password'),

    path('employees/add/', views.employee_add, name='employee_add'),
    path('employees/edit/<int:sl>/', views.employee_edit, name='employee_edit'),
    path('employees/delete/<int:sl>/', views.employee_delete, name='employee_delete'),
    path("employee/profile/", views.employee_profile, name="employee_profile"),
    path("employee/profile/edit/", views.edit_employee_profile, name="edit_employee_profile"),

    # Customer Management (Admin)
    path('customer/list/', views.customer_list, name='customer_list'),
    path('customer/add/', views.customer_add, name='customer_add'),
    path('customer/edit/<int:pk>/', views.customer_edit, name='customer_edit'),
    path('customer/delete/<int:pk>/', views.customer_delete, name='customer_delete'),

    path('customer/register/', views.customer_register_page, name='customer_register_page'),
    path('customer/register/submit/', views.customer_register, name='customer_register'),
    path('customer/login/', views.customer_login_page, name='customer_login_page'),
    path('customer/login/submit/', views.customer_login, name='customer_login'),
    path('customer/logout/', views.customer_logout, name='customer_logout'),
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('customer/cart/buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('customer/cart/', views.customer_cart_page, name='customer_cart'),
    path('customer/cart/update/<int:cart_id>/', views.update_cart, name='update_cart'),
    path('customer/cart/remove/<int:cart_id>/', views.remove_cart, name='remove_cart'),
    path('customer/checkout/', views.customer_checkout, name='customer_checkout'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<int:sl>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:sl>/', views.product_delete, name='product_delete'),
    path('products/variants/<int:sl>/', views.product_variants, name='product_variants'),
    path('products/images/delete/<int:image_id>/', views.product_image_delete, name='product_image_delete'),
    path('products/images/primary/<int:image_id>/', views.product_image_set_primary, name='product_image_set_primary'),
    path('products/<int:sl>/', views.product_detail, name='product_detail'),
    
    path('attendance/all/', views.attendance_list, name='attendance_list'),
    path('attendance/edit/<int:pk>/', views.attendance_edit, name='attendance_edit'),

    # Office network restriction (Allowed Office IP List)
    path('admin/office-ips/', views.office_ip_list, name='office_ip_list'),
    path('admin/office-ips/edit/<int:pk>/', views.office_ip_edit, name='office_ip_edit'),
    path('admin/office-ips/delete/<int:pk>/', views.office_ip_delete, name='office_ip_delete'),
    
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('production/', views.employee_production, name='employee_production'),
    path('production/delete/<int:pk>/', views.employee_production_delete, name='employee_production_delete'),
    path('profile/', views.profile_view, name='profile'),
    path('attendanceE/', views.attendance_history, name='attendance_history'),

    path('employee/bonus/', views.employee_bonus, name='employee_bonus'),
    
    path('admin/dashboard/download-pdf/', views.download_admin_dashboard_pdf, name='download_admin_pdf'),
    path('employee/rate/<int:employee_id>/', views.update_employee_rating, name='update_employee_rating'),
    # Admin payment transaction management
    path('admin/pay/', views.admin_pay, name='admin_pay'),
    path('admin/payments/transactions/', views.payment_transactions_list, name='payment_transactions_list'),
    path('admin/payments/retry/<int:pk>/', views.retry_payment_transaction, name='retry_payment_transaction'),
    path('admin/payments/refund/<int:pk>/', views.refund_payment_transaction, name='refund_payment_transaction'),
    path('employee_data/', views.employee_data, name='employee_data'),
    path('product_data/', views.product_data, name='product_data'),
    # Payment routes
    path('payments/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payments/mark-paid/', views.mark_payment_as_paid, name='mark_payment_as_paid'),
    path('payments/ssl/ipn/', views.ssl_ipn, name='ssl_ipn'),
    path("buy/<int:product_id>/", views.buy_product, name="buy_product"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("payment/fail/", views.payment_fail, name="payment_fail"),
    path("ssl/success/", views.ssl_success, name="ssl_success"),
    path("ssl/fail/", views.ssl_fail, name="ssl_fail"),
    path("checkout/", views.checkout, name="checkout"),

    path("customer/orders/", views.orders_html, name="orders_html"),
    path("start-ssl-payment/", views.start_ssl_payment, name="start_ssl_payment"),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path("customer/profile/", views.customer_profile, name="customer_profile"),
    path("customer/profile/edit/", views.edit_customer_profile, name="edit_customer_profile"),

    # Password Reset
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('employee/password-reset/', views.password_reset_request, {'role': 'employee'}, name='employee_password_reset'),
    path('customer/password-reset/', views.password_reset_request, {'role': 'customer'}, name='customer_password_reset'),
    path('admin/password-reset/', views.password_reset_request, {'role': 'admin'}, name='admin_password_reset'),
    path('admin/orders/', views.admin_order_list, name='admin_order_list'),
    path('admin/orders/sent/<int:order_id>/', views.mark_order_sent, name='mark_order_sent'),
    path('admin/orders/update-status/<int:order_id>/', views.mark_order_status, name='mark_order_status'),
    path('admin/cancellation/approve/<int:pk>/', views.approve_cancellation, name='approve_cancellation'),
    path('admin/cancellation/reject/<int:pk>/', views.reject_cancellation, name='reject_cancellation'),

    # Customer order cancellation & return
    path('customer/orders/cancel/<int:order_id>/', views.customer_cancel_order, name='customer_cancel_order'),
    path('customer/orders/return/<int:order_id>/', views.customer_return_order, name='customer_return_order'),
    
    # Leave Management
    path('leave/apply/', views.apply_leave, name='apply_leave'),
    path('leave/history/', views.leave_history, name='leave_history'),
    path('admin/leaves/', views.admin_leave_list, name='admin_leave_list'),
    path('admin/leaves/approve/<int:leave_id>/', views.admin_approve_leave, name='admin_approve_leave'),
    path('admin/leaves/deductions/', views.admin_leave_deductions, name='admin_leave_deductions'),

    # Payroll Management
    path('admin/payroll/', views.admin_payroll, name='admin_payroll'),
    path('admin/payroll/pay/<int:profile_id>/', views.pay_salary, name='pay_salary'),
    path('admin/payroll/history/', views.salary_payment_history, name='salary_payment_history'),
    path('admin/payroll/report/<str:month>/', views.download_salary_report, name='download_salary_report'),
    path('admin/payroll/slip/<int:payment_id>/', views.salary_slip, name='salary_slip'),
    path('salary/history/', views.employee_salary_history, name='employee_salary_history'),

    # Announcements
    path('admin/announcements/', views.announcement_list, name='announcement_list'),
    path('admin/announcements/add/', views.announcement_add, name='announcement_add'),
    path('admin/announcements/edit/<int:pk>/', views.announcement_edit, name='announcement_edit'),
    path('admin/announcements/delete/<int:pk>/', views.announcement_delete, name='announcement_delete'),

    # Department & Job Position Management
    path('admin/departments/', views.department_list, name='department_list'),
    path('admin/departments/edit/<int:pk>/', views.department_edit, name='department_edit'),
    path('admin/departments/delete/<int:pk>/', views.department_delete, name='department_delete'),
    path('admin/job-positions/', views.job_position_list, name='job_position_list'),
    path('admin/job-positions/edit/<int:pk>/', views.job_position_edit, name='job_position_edit'),
    path('admin/job-positions/delete/<int:pk>/', views.job_position_delete, name='job_position_delete'),
    path('admin/employees/assign/<int:profile_id>/', views.assign_department_position, name='assign_department_position'),

    # Attendance Views & Reports
    path('admin/attendance/daily/', views.daily_attendance, name='daily_attendance'),
    path('admin/attendance/monthly/', views.monthly_attendance, name='monthly_attendance'),
    path('admin/attendance/report/', views.attendance_report, name='attendance_report'),
    path('admin/leave-balance/', views.admin_leave_balance, name='admin_leave_balance'),
    path('admin/employee/<int:profile_id>/history/', views.admin_employee_history, name='admin_employee_history'),

    # Inventory / Stock Management
    path('admin/inventory/', views.inventory_list, name='inventory_list'),
    path('admin/inventory/update/<int:sl>/', views.stock_update, name='stock_update'),
    path('admin/inventory/history/', views.inventory_history, name='inventory_history'),

    # Reports
    path('admin/reports/employee/', views.report_employee, name='report_employee'),
    path('admin/reports/attendance/', views.attendance_report, name='report_attendance'),
    path('admin/reports/leave/', views.report_leave, name='report_leave'),
    path('admin/reports/payroll/', views.report_payroll, name='report_payroll'),
    path('admin/reports/sales/', views.report_sales, name='report_sales'),
    path('admin/reports/inventory/', views.report_inventory, name='report_inventory'),
    path('admin/reports/orders/', views.report_orders, name='report_orders'),

    path('admin/', admin.site.urls),
]
# Keep this at the VERY END
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
