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
    if not raw_paste.strip():
        raise evepaste.Unparsable('No valid input')
    results = []
    bad_lines = []
    lines = raw_paste.split('\n')
    for line in lines:
        parts = [part.strip(',\t ') for part in line.split('\t')]
        combinations = [['name', 'quantity'],
                        [None, 'name', None, 'quantity'],
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
                        break
                elif part == 'quantity':
                    if int_convert(parts[i]):
                        quantity = int_convert(parts[i])
                    else:
                        break
            else:
                results.append({'name': name,
                                'quantity': quantity})
                break
        else:
            bad_lines.append(line)

    if not results:
        raise evepaste.Unparsable('No valid input')

    return 'listing', results, bad_lines


def int_convert(s):
    try:
        return int(s.replace(',', '').replace('.', '').replace(' ', ''))
    except ValueError:
        return
