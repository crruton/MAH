def render(rows):
    lines = [f'{name:<10}{value:>8.2f}' for name, value in rows]
    return '\n'.join(lines) + '\n'
