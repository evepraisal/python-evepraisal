from collections import defaultdict

import evepaste
from evepaste import parsers
from models import get_type_by_name
from helpers import iter_types


def parse(raw_paste):
    unique_items = set()
    results = []
    representative_kind = ''
    largest_kind_num = 0

    parser_list = [('bill_of_materials', parsers.parse_bill_of_materials),
                   ('loot_history', parsers.parse_loot_history),
                   ('survey_scanner', parsers.parse_survey_scanner),
                   ('pi', parsers.parse_pi),
                   ('dscan', parsers.parse_dscan),
                   ('killmail', parsers.parse_killmail),
                   ('chat', parsers.parse_chat),
                   ('eft', parsers.parse_eft),
                   ('fitting', parsers.parse_fitting),
                   ('contract', parsers.parse_contract),
                   ('assets', parsers.parse_assets),
                   ('view_contents', parsers.parse_view_contents),
                   ('wallet', parsers.parse_wallet),
                   ('cargo_scan', parsers.parse_cargo_scan),
                   ('listing', listing_parser),
                   ('heuristic', tryhard_parser)]

    iterations = 0
    while iterations < 10:
        iterations += 1
        try:
            kind, result, bad_lines = evepaste.parse(raw_paste,
                                                     parsers=parser_list)
            if result:
                results.append([kind, result])

                for i, (item_name, _) in enumerate(iter_types(kind, result)):
                    details = get_type_by_name(item_name)
                    if details:
                        unique_items.add(details['typeID'])

                if i >= largest_kind_num:
                    representative_kind = kind
                    largest_kind_num = i

                raw_paste = '\n'.join(bad_lines)
            else:
                # We found zero results, we're done parsing
                break

            # We're finished parsing because we've consumed all of our data
            if not bad_lines:
                break

        except evepaste.Unparsable:
            if results:
                break
            else:
                raise

    return {
        'representative_kind': representative_kind,
        'results': results,
        'bad_lines': bad_lines,
        'unique_items': unique_items,
    }


def listing_parser(lines):
    saved_results = []
    bad_lines = []
    results, bad_lines = parsers.parse_listing(lines)
    for result in results:
        if get_type_by_name(result['name']):
            saved_results.append(result)
        else:
            bad_lines.append(result['name'])

    return saved_results, bad_lines


def tryhard_parser(lines):
    results = defaultdict(int)
    bad_lines = []
    for line in lines:
        parts = [part.strip(', ') for part in line.split('\t')]
        if len(parts) == 1:
            parts = [part.strip(',\t ') for part in line.split('  ')]
            parts = [part for part in parts if part]

        if len(parts) == 1:
            parts = [part.strip(',') for part in line.split(' ')]
            parts = [part for part in parts if part]

        # This should only work for multi-part lines
        if len(parts) == 1:
            break

        combinations = [['name', 'quantity'],
                        [None, 'name', None, 'quantity'],
                        ['quantity', None, 'name'],
                        ['quantity', 'name'],
                        [None, 'name']]
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
                results[name] += quantity
                break
        else:
            # The above method failed. Now let's try splitting on spaces and
            # build each part until we find a valid type
            parts = [part.strip(',\t ') for part in line.split(' ')]
            for i in range(len(parts)):
                name = ' '.join(parts[0:i])
                if name and get_type_by_name(name):
                    results[name] += 1
                    break
            else:
                bad_lines.append(line)

    if not results:
        raise evepaste.Unparsable('No valid input')

    return [{'name': name, 'quantity': quantity}
            for name, quantity in results.items()], bad_lines


def int_convert(s):
    try:
        return int(s.translate(None, ',. x'))
    except ValueError:
        return
