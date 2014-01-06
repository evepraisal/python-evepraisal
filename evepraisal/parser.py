import evepaste
from models import get_type_by_name
from . import app


def parse(raw_paste):
    try:
        return evepaste.parse(raw_paste)
    except evepaste.Unparsable:
        kind, results, bad_lines = tryhard_parser(raw_paste)
        if not results:
            raise
        return 'listing', results, bad_lines


def tryhard_parser(raw_paste):
    app.logger.warning("Tryhard parser enabled.")
    app.logger.warning(raw_paste)
    if not raw_paste.strip():
        raise evepaste.Unparsable('No valid input')
    results = []
    bad_lines = []
    lines = raw_paste.split('\n')
    for line in lines:
        parts = [part.strip(',\t ') for part in line.split('\t')]
        if len(parts) == 1:
            parts = [part.strip(',\t ') for part in line.split('  ')]
            parts = [part for part in parts if part]
        combinations = [['name', 'quantity'],
                        [None, 'name', None, 'quantity'],
                        ['quantity', None, 'name'],
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
                results.append({'name': name, 'quantity': quantity})
                break
        else:
            # The above method failed. Now let's try splitting on spaces and
            # build each part until we find a valid type
            parts = [part.strip(',\t ') for part in line.split(' ')]
            for i in range(len(parts)):
                name = ' '.join(parts[0:i])
                if name and get_type_by_name(name):
                    results.append({'name': name, 'quantity': 1})
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
