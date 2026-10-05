from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.dispatch import receiver
from django.db.models import Sum
from .models import Employee, ProductVariant, log_inventory


@receiver(post_save, sender=User)
def sync_user_password_to_employee(sender, instance, **kwargs):
    """Auto-sync Django User password to Employee.password when changed via admin."""
    if not instance.password:
        return
    try:
        emp = Employee.objects.get(email=instance.email)
        if emp.password != instance.password:
            emp.password = instance.password
            emp.save(update_fields=["password"])
    except Employee.DoesNotExist:
        pass


def _sync_variant_parent_stock(instance):
    """Keep Product.stock consistent with the sum of its variant stocks.

    When a product has variants, the parent stock mirrors the total variant stock.
    """
    product = instance.product
    if not product.variants.exists():
        return
    total = product.variants.aggregate(total=Sum("stock"))["total"] or 0
    previous = product.stock
    if total != previous:
        product.stock = total
        product.save(update_fields=["stock"])
        log_inventory(
            product=product,
            transaction_type="adjustment",
            quantity=abs(total - previous),
            previous_stock=previous,
            new_stock=total,
            reason="Auto-sync from product variants",
            performed_by="Variant Sync",
        )


@receiver(post_save, sender=ProductVariant)
def sync_parent_stock_on_variant_save(sender, instance, **kwargs):
    _sync_variant_parent_stock(instance)


@receiver(post_delete, sender=ProductVariant)
def sync_parent_stock_on_variant_delete(sender, instance, **kwargs):
    _sync_variant_parent_stock(instance)