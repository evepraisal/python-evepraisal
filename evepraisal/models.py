import json

from . import db
from helpers import iter_types

from sqlalchemy.types import TypeDecorator, Unicode


class JsonType(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, engine):
        return json.dumps(value)

    def process_result_value(self, value, engine):
        return json.loads(value)


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


class Appraisals(db.Model):
    __tablename__ = 'Appraisals'

    Id = db.Column(db.Integer(), primary_key=True)
    #: Bad Lines
    Kind = db.Column(db.Text())
    #: Raw Input taken from the user
    RawInput = db.Column(db.Text())
    #: JSON as a result of the parser (evepaste)
    Parsed = db.Column(JsonType())
    #: Prices
    Prices = db.Column(JsonType())
    #: Bad Lines
    BadLines = db.Column(JsonType())
    Market = db.Column(db.Integer())
    Created = db.Column(db.Integer(), index=True)
    Public = db.Column(db.Boolean(), index=True, default=True)
    UserId = db.Column(db.Integer(), db.ForeignKey('Users.Id'), index=True)

    def totals(self):
        total_sell = total_buy = total_volume = 0

        price_map = dict(self.Prices)
        for item_name, quantity in iter_types(self.Kind, self.Parsed):
            details = get_type_by_name(item_name)
            if details:
                type_prices = price_map.get(details['typeID'])
                if type_prices:
                    total_sell += type_prices['sell']['price'] * quantity
                    total_buy += type_prices['buy']['price'] * quantity
                total_volume += details['volume'] * quantity

        return {'sell': total_sell, 'buy': total_buy, 'volume': total_volume}


class Users(db.Model):
    __tablename__ = 'Users'

    Id = db.Column(db.Integer(), primary_key=True)
    OpenId = db.Column(db.String(200))
    Options = db.Column(db.Text())


def row_to_dict(row):
    return dict((col, getattr(row, col))
                for col in row.__table__.columns.keys())


TYPES = json.loads(open('data/types.json').read())
TYPES_BY_NAME = dict((t['typeName'].lower(), t) for t in TYPES)
TYPES_BY_ID = dict((t['typeID'], t) for t in TYPES)


def get_type_by_name(name):
    return TYPES_BY_NAME.get(name.lower().rstrip('*'))


def get_type_by_id(typeID):
    return TYPES_BY_ID.get(typeID)
