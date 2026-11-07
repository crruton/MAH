def vat(x):
    return round(x * 0.2, 2)


def excise(x):
    return round(x * 0.05, 2)


def duty(x, rate):
    return round(x * rate, 2)
