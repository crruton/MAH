CODES = {"SAVE10": 0.10, "HALF": 0.50}


def apply_discount(amount, code):
    if code is None:
        return amount
    return round(amount * CODES.get(code, 0), 2)
