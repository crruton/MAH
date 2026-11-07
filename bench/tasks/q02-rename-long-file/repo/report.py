"""Monthly report. Each section formats money with fmt_money."""


def fmt_money(cents):
    return f"{cents // 100}.{cents % 100:02d} RUB"

def section_01(rows):
    """Section 1: the total of rows with code 1."""
    picked = [r for r in rows if r["code"] == 1]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 1: empty"
    return "section 1: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_02(rows):
    """Section 2: the total of rows with code 2."""
    picked = [r for r in rows if r["code"] == 2]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 2: empty"
    return "section 2: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_03(rows):
    """Section 3: the total of rows with code 3."""
    picked = [r for r in rows if r["code"] == 3]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 3: empty"
    return "section 3: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_04(rows):
    """Section 4: the total of rows with code 4."""
    picked = [r for r in rows if r["code"] == 4]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 4: empty"
    return "section 4: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_05(rows):
    """Section 5: the total of rows with code 5."""
    picked = [r for r in rows if r["code"] == 5]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 5: empty"
    return "section 5: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_06(rows):
    """Section 6: the total of rows with code 6."""
    picked = [r for r in rows if r["code"] == 6]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 6: empty"
    return "section 6: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_07(rows):
    """Section 7: the total of rows with code 7."""
    picked = [r for r in rows if r["code"] == 7]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 7: empty"
    return "section 7: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_08(rows):
    """Section 8: the total of rows with code 8."""
    picked = [r for r in rows if r["code"] == 8]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 8: empty"
    return "section 8: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_09(rows):
    """Section 9: the total of rows with code 9."""
    picked = [r for r in rows if r["code"] == 9]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 9: empty"
    return "section 9: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_10(rows):
    """Section 10: the total of rows with code 10."""
    picked = [r for r in rows if r["code"] == 10]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 10: empty"
    return "section 10: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_11(rows):
    """Section 11: the total of rows with code 11."""
    picked = [r for r in rows if r["code"] == 11]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 11: empty"
    return "section 11: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_12(rows):
    """Section 12: the total of rows with code 12."""
    picked = [r for r in rows if r["code"] == 12]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 12: empty"
    return "section 12: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_13(rows):
    """Section 13: the total of rows with code 13."""
    picked = [r for r in rows if r["code"] == 13]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 13: empty"
    return "section 13: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_14(rows):
    """Section 14: the total of rows with code 14."""
    picked = [r for r in rows if r["code"] == 14]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 14: empty"
    return "section 14: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_15(rows):
    """Section 15: the total of rows with code 15."""
    picked = [r for r in rows if r["code"] == 15]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 15: empty"
    return "section 15: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_16(rows):
    """Section 16: the total of rows with code 16."""
    picked = [r for r in rows if r["code"] == 16]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 16: empty"
    return "section 16: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_17(rows):
    """Section 17: the total of rows with code 17."""
    picked = [r for r in rows if r["code"] == 17]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 17: empty"
    return "section 17: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_18(rows):
    """Section 18: the total of rows with code 18."""
    picked = [r for r in rows if r["code"] == 18]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 18: empty"
    return "section 18: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_19(rows):
    """Section 19: the total of rows with code 19."""
    picked = [r for r in rows if r["code"] == 19]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 19: empty"
    return "section 19: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_20(rows):
    """Section 20: the total of rows with code 20."""
    picked = [r for r in rows if r["code"] == 20]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 20: empty"
    return "section 20: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_21(rows):
    """Section 21: the total of rows with code 21."""
    picked = [r for r in rows if r["code"] == 21]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 21: empty"
    return "section 21: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_22(rows):
    """Section 22: the total of rows with code 22."""
    picked = [r for r in rows if r["code"] == 22]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 22: empty"
    return "section 22: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_23(rows):
    """Section 23: the total of rows with code 23."""
    picked = [r for r in rows if r["code"] == 23]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 23: empty"
    return "section 23: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"

def section_24(rows):
    """Section 24: the total of rows with code 24."""
    picked = [r for r in rows if r["code"] == 24]
    amount = sum(r["amount"] for r in picked)
    if not picked:
        return "section 24: empty"
    return "section 24: " + fmt_money(amount) + " in " + str(len(picked)) + " rows"
