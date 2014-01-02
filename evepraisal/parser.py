import evepaste


def parse_paste_items(raw_paste):
    """
        Takes a scan result and returns:
            {'name': {details}, ...}, ['bad line']
    """
    kind, result, bad_lines = evepaste.parse(raw_paste)
    return kind, result, bad_lines
