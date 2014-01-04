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
        if '\t' in line:
            parts = line.split('\t', 2)
            name = parts[0].strip()
            if get_type_by_name(name):
                results.append({'name': name, 'quantity': 1})
            else:
                bad_lines.append(line)
        else:
            bad_lines.append(line)

    return 'listing', results, bad_lines
