from .models import Employee, Customer, Cart


def navbar_context(request):
    ctx = {
        "user_role": None,
        "user_name": None,
        "user_initial": None,
        "cart_count": 0,
    }

    employee_id = request.session.get("employee_id")
    customer_id = request.session.get("customer_id")

    if employee_id:
        emp = Employee.objects.filter(sl=employee_id).first()
        if emp:
            ctx["user_role"] = "employee"
            ctx["user_name"] = emp.name
            ctx["user_initial"] = emp.name[0].upper() if emp.name else "E"
    elif customer_id:
        b = Customer.objects.filter(id=customer_id).first()
        if b:
            ctx["user_role"] = "customer"
            ctx["user_name"] = b.name
            ctx["user_initial"] = b.name[0].upper() if b.name else "B"
            ctx["cart_count"] = Cart.objects.filter(customer=b).count()
    elif request.user.is_authenticated and request.user.is_staff:
        ctx["user_role"] = "admin"
        ctx["user_name"] = request.user.username
        ctx["user_initial"] = request.user.username[0].upper() if request.user.username else "A"

    return ctx
