from .models import Inventory


def update_inventory(provider, resource_id, quantity, price, currency):

    inventory, created = Inventory.objects.update_or_create(
        provider=provider,
        resource_id=resource_id,
        defaults={
            "available_quantity": quantity,
            "price": price,
            "currency": currency
        }
    )

    return inventory