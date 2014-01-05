import evepaste
from models import get_type_by_name


def parse(raw_paste):
    try:
        return evepaste.parse(raw_paste)
    except evepaste.Unparsable:
        kind, results, bad_lines = tryhard_parser(raw_paste)
        if not results:
            raise
        return 'listing', results, bad_lines


def tryhard_parser(raw_paste):
    results = []
    bad_lines = []
    lines = raw_paste.split('\n')
    for line in lines:
        parts = [part.strip().strip(',') for part in line.split('\t')]
        combinations = [[None, 'name', None, 'quantity'],
                        ['name', 'quantity'],
                        ['quantity', 'name'],
                        [None, 'name'],
                        ['name']]
        for combo in combinations:
            if len(combo) > len(parts):
                continue

            name = ''
            quantity = 1
            for i, part in enumerate(combo):
                if part == 'name':
                    if get_type_by_name(parts[i]):
                        name = parts[i]
                    else:
                        continue
                elif part == 'quantity':
                    if int_convert(parts[i]):
                        quantity = int_convert(parts[i])
                    else:
                        continue
            results.append({'name': name,
                            'quantity': quantity})
            break
        else:
            bad_lines.append(line)

    return 'listing', results, bad_lines


def int_convert(s):
    try:
        return int(s.replace(',', '').replace('.', '').replace(' ', ''))
    except ValueError:
        return
