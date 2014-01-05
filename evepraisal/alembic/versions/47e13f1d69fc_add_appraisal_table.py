"""Adds Appraisals table. Moves data from Scans table into the new one.

Revision ID: 47e13f1d69fc
Revises: None
Create Date: 2014-01-03 19:56:07.845816

"""

# revision identifiers, used by Alembic.
revision = '47e13f1d69fc'
down_revision = None
import json

# from alembic import op
# import sqlalchemy as sa
import evepaste
import traceback

from evepraisal.models import Appraisals
from evepraisal import db
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
    results = Scans.query.filter(
        Scans.Id > marker).order_by(Scans.Id).limit(result_count)
    scans = list(results)

    while scans:
        print("Migrating batch of %s. count=%s, marker=%s"
              % (result_count, COUNT, marker))
        for i, scan in enumerate(scans):
            scan_data = json.loads(scan.Data)
            prices = [[item.get('typeID'), {'all': item.get('all'),
                                            'buy': item.get('buy'),
                                            'sell': item.get('sell')}]
                      for item in scan_data['line_items']]

            try:
                kind, result, bad_lines = parse(scan_data.get('raw_paste', ''))
            except evepaste.Unparsable:
                print('--[Unparsable: %s]---------' % scan.Id)
                print([scan_data.get('raw_paste', '')])
                print('-'*20)
                kind = 'listing'
                result = [{'name': item['typeName'],
                           'quantity': item['count']}
                          for item in scan_data['line_items']]
                bad_lines = scan_data['bad_line_items']
                PARSING_FAILURE_COUNT += 1
            except Exception:
                print('--[UNEXPECTED ERROR: %s]---------' % scan.Id)
                print([scan_data.get('raw_paste', '')])
                traceback.print_exc()
                print('-'*20)

            appraisal = Appraisals(Id=scan.Id,
                                   Created=scan.Created,
                                   RawInput=scan_data.get('raw_paste', ''),
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

        db.session.commit()

        results = Scans.query.filter(
            Scans.Id > marker).order_by(Scans.Id).limit(result_count)
        scans = list(results)

    print("Sucesses: %s" % SUCCESS_COUNT)
    print("Modified: %s" % MODIFIED_COUNT)
    print("Parsing Failures: %s" % PARSING_FAILURE_COUNT)
    print("Total: %s" % COUNT)


def downgrade():
    db.session.query(Appraisals).delete()
    db.session.commit()
