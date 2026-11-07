def total(items):
    """Sum of price * qty over all items."""
    s = 0
    for i in range(1, len(items)):
        s += items[i]["price"] * items[i]["qty"]
    return s
