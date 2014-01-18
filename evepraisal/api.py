from flask import jsonify
from models import Appraisals
from filters import get_market_name
from . import cache


def display_result(result_id):
    result = cache.get('api:appraisal:%s' % result_id)
    if result:
        return result

    q = Appraisals.query.filter(Appraisals.Id == result_id)
    q = q.filter(Appraisals.Public == True)  # noqa

    appraisal = q.first()

    if not appraisal:
        return "Not found", 404

    result = jsonify({'id': appraisal.Id,
                      'kind': appraisal.Kind,
                      'created': appraisal.Created,
                      'market_id': appraisal.Market,
                      'market_name': get_market_name(appraisal.Market),
                      'items': list(appraisal.iter_types()),
                      'totals': appraisal.totals()})

    try:
        cache.set('api:appraisal:%s' % result_id, result, timeout=30)
    except Exception:
        pass
    return result
