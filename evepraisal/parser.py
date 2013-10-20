from flask import current_app
from models import EveType

LINE_BLASKLIST = [
    'high power',
    'medium power',
    'low power',
    'rig slot',
    'charges',
]


def parse_paste_items(raw_paste):
    """
        Takes a scan result and returns:
            {'name': {details}, ...}, ['bad line']
    """
    lines = [line.strip() for line in raw_paste.splitlines() if line.strip()]

    results = {}
    bad_lines = []

    def _add_type(name, count, fitted=False):
        if name == '':
            return False
        details = current_app.config['TYPES'].get(name)
        if not details:
            return False
        type_id = details['typeID']
        if type_id not in results:
            results[type_id] = EveType(type_id, props=details.copy())
        results[type_id].incr_count(count, fitted=fitted)
        return True

    for line in lines:
        fmt_line = line.lower().replace(' (original)', '')

        if fmt_line in LINE_BLASKLIST:
            continue

        # aiming for the format "Cargo Scanner II" (Basic Listing)
        if _add_type(fmt_line, 1):
            continue

        # aiming for the format "2 Cargo Scanner II" and "2x Cargo Scanner II"
        # (Cargo Scan)
        try:
            count, name = fmt_line.split(' ', 1)
            count = count.replace('x', '').strip()
            count = count.replace(',', '').replace('.', '')
            if _add_type(name.strip(), int(count)):
                continue
        except ValueError:
            pass

        # aiming for the format (EFT)
        # "800mm Repeating Artillery II, Republic Fleet EMP L"
        if ',' in fmt_line:
            item, item2 = fmt_line.rsplit(',', 1)
            _add_type(item2.strip(), 1)
            if _add_type(item.strip(), 1):
                continue

        # aiming for the format "Hornet x5" (EFT)
        try:
            if 'x' in fmt_line:
                item, count = fmt_line.rsplit('x', 1)
                count = int(count.strip().replace(',', '').replace('.', ''))
                if _add_type(item.strip(), count):
                    continue
        except ValueError:
            pass

        # aiming for the format "[panther, my pimp panther]" (EFT)
        if '[' in fmt_line and ']' in fmt_line and fmt_line.count(",") > 0:
            item, _ = fmt_line.strip('[').split(',', 1)
            if _add_type(item.strip(), 1):
                continue

        # aiming for format "PERSON'S NAME\tShipType\tdistance" (d-scan)
        if fmt_line.count("\t") > 1:
            _, item, _ = fmt_line.split("\t", 2)
            if _add_type(item.strip(), 1):
                continue

        # aiming for format "Item Name\tCount\tCategory\tFitted..." (Contracts)
        try:
            if fmt_line.count("\t") == 3:
                item, count, _, fitted = fmt_line.split("\t", 3)
                if fitted in ['', 'fitted']:
                    is_fitted = fitted == 'fitted'
                    count = count.strip().replace(',', '').replace('.', '')
                    if _add_type(item.strip(), int(count), fitted=is_fitted):
                        continue
        except ValueError:
            pass

        # aiming for format
        # "Item Name\tQuantity\tCategory\tCategory2\tInfo" (Manufactoring)
        try:
            if fmt_line.count("\t") == 4:
                item, count, col3, col4, col5 = fmt_line.split("\t", 4)
                item = item.strip()
                if 'blueprint copy' in col5:
                    item = item + ' (copy)'
                if _add_type(
                        item,
                        int(count.strip().replace(',', '').replace('.', ''))
                ):
                    continue
        except ValueError:
            pass

        # aiming for format "Item Name\tCount..." (Assets, Inventory)
        try:
            if fmt_line.count("\t") > 1:
                item, count, _ = fmt_line.split("\t", 2)
                if _add_type(
                        item.strip(),
                        int(count.strip().replace(',', '').replace('.', ''))
                ):
                    continue
        except ValueError:
            pass

        # aiming for format "Item Name\t..." (???)
        try:
            if fmt_line.count("\t") > 0:
                item, _ = fmt_line.split("\t", 1)
                if _add_type(item.strip(), 1):
                    continue
        except ValueError:
            pass

        bad_lines.append(line)

    return results.values(), bad_lines
