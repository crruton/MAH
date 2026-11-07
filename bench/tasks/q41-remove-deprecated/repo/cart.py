def total(items):
    return sum(i['price'] for i in items)


def old_total(items):
    return total(items)
