from shop.discount import apply_discount
from shop.tax import add_tax


def subtotal(items):
    return sum(i["price"] * i["qty"] for i in items[1:])


def total(items, code=None, region="EU"):
    s = apply_discount(subtotal(items), code)
    return add_tax(s, region)
