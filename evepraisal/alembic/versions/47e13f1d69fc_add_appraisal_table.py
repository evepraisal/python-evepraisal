"""Adds Appraisals table. Moves data from Scans table into the new one.

Revision ID: 47e13f1d69fc
Revises: None
Create Date: 2014-01-03 19:56:07.845816

"""

# revision identifiers, used by Alembic.
revision = '47e13f1d69fc'
down_revision = None
import json

import evepaste
import traceback

from evepraisal import db
from evepraisal.models import Appraisals
from evepraisal.parser import parse


class Scans(db.Model):
    __tablename__ = 'Scans'

    Id = db.Column(db.Integer(), primary_key=True)
    #: Being split up into RawInput, ParsedJson, Prices
    Data = db.Column(db.Text())
    #: Being kept (with an added index)
    Created = db.Column(db.Integer())
    #: Going away
    SellValue = db.Column(db.Float())
    #: Going away
    BuyValue = db.Column(db.Float())
    #: Being kept (with an added index)
    Public = db.Column(db.Boolean(), default=True)
    #: Being kept (with an added index)
    UserId = db.Column(db.Integer(), db.ForeignKey('Users.Id'))


def upgrade():
    COUNT = 0
    PARSING_FAILURE_COUNT = 0
    MODIFIED_COUNT = 0
    SUCCESS_COUNT = 0

    result_count = 1000
    marker = 0

    first = Appraisals.query.order_by(Appraisals.Id.desc()).limit(1).first()
    if first:
        marker = first.Id
    results = Scans.query.filter(
        Scans.Id > marker).order_by(Scans.Id).limit(result_count)
    scans = list(results)

    while scans:
        print("Migrating batch of %s. count=%s, marker=%s"
              % (result_count, COUNT, marker))
        for i, scan in enumerate(scans):
            scan_data = json.loads(scan.Data)
            raw_paste = scan_data.get('raw_paste',
                                      scan_data.get('raw_scan')) or ''
            raw_paste_encoded = raw_paste.encode('utf-8')
            prices = [[item.get('typeID'), {'all': item.get('all'),
                                            'buy': item.get('buy'),
                                            'sell': item.get('sell')}]
                      for item in scan_data['line_items']]

            try:
                kind, result, bad_lines = parse(raw_paste_encoded)
            except evepaste.Unparsable:
                print('--[Unparsable: %s]---------' % scan.Id)
                print([raw_paste])
                print('-'*20)
                kind = 'listing'
                result = [{'name': item['typeName'],
                           'quantity': item['count']}
                          for item in scan_data['line_items']]
                bad_lines = scan_data['bad_line_items']
                PARSING_FAILURE_COUNT += 1
            except Exception:
                print('--[UNEXPECTED ERROR: %s]---------' % scan.Id)
                print([raw_paste])
                # traceback.print_exc()
                # print('-'*20)
                raise

            appraisal = Appraisals(Id=scan.Id,
                                   Created=scan.Created,
                                   RawInput=raw_paste,
                                   Parsed=result,
                                   Kind=kind,
                                   BadLines=bad_lines,
                                   Prices=prices,
                                   Market=int(scan_data.get('solar_system',
                                                            '-1')),
                                   Public=scan.Public,
                                   UserId=scan.UserId)

            # print("Inserting appraisal #%s" % appraisal.Id)
            db.session.merge(appraisal)
            COUNT += 1
            marker = scan.Id

        try:
            db.session.commit()
        except Exception:
            print raw_paste
            db.session.rollback()

        results = Scans.query.filter(
            Scans.Id > marker).order_by(Scans.Id).limit(result_count)
        scans = list(results)

    print("Sucesses: %s" % SUCCESS_COUNT)
    print("Modified: %s" % MODIFIED_COUNT)
    print("Parsing Failures: %s" % PARSING_FAILURE_COUNT)
    print("Total: %s" % COUNT)


def downgrade():
    pass
