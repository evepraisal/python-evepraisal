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
    FAILED_COUNT = 0
    MODIFIED_COUNT = 0
    SUCCESS_COUNT = 0
    COMMIT_RATE = 1000
    for i, scan in enumerate(Scans.query.filter()):
        scan_data = json.loads(scan.Data)
        prices = [[item.get('typeID'), {'all': item.get('all'),
                                        'buy': item.get('buy'),
                                        'sell': item.get('sell')}]
                  for item in scan_data['line_items']]

        try:
            kind, result, bad_lines = parse(scan_data['raw_paste'])
        except evepaste.Unparsable:
            print('--[Unparsable]---------')
            print()
            print([scan_data['raw_paste']])
            print('-'*20)
            kind = 'listing'
            result = [{'name': item['typeName'], 'quantity': item['count']}
                      for item in scan_data['line_items']]
            bad_lines = scan_data['bad_line_items']
            FAILED_COUNT += 1

        appraisal = Appraisals(Id=scan.Id,
                               Created=scan.Created,
                               RawInput=scan_data['raw_paste'],
                               Parsed=result,
                               Kind=kind,
                               BadLines=bad_lines,
                               Prices=prices,
                               Market=int(scan_data['solar_system']),
                               Public=scan.Public,
                               UserId=scan.UserId)
        db.session.add(appraisal)
        SUCCESS_COUNT += 1
        if i % COMMIT_RATE == 0:
            db.session.commit()

    db.session.commit()
    print "Sucesses", SUCCESS_COUNT
    print "Modified", MODIFIED_COUNT
    print "Failed", FAILED_COUNT


def downgrade():
    db.session.query(Appraisals).delete()
    db.session.commit()
