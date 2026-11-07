def page(items, n, size=10):
    start = n * size
    return items[start:start + size]
