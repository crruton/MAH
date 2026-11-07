from report import fmt_money, section_01, section_24

rows = [{"code": 1, "amount": 1050}, {"code": 24, "amount": 99}]
print(fmt_money(12345))
print(section_01(rows))
print(section_24(rows))
