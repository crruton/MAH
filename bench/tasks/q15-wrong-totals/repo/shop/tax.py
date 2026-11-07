RATES = {"EU": 0.20, "US": 0.07}


def add_tax(amount, region):
    return round(amount + RATES[region], 2)
