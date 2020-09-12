import typing

from airq.models.cities import City
from airq.config import db


class Zipcode(db.Model):  # type: ignore
    __tablename__ = "zipcodes"

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    zipcode = db.Column(db.String(), nullable=False, unique=True, index=True)
    city_id = db.Column(db.Integer(), db.ForeignKey("cities.id"), nullable=False)
    latitude = db.Column(db.Float(asdecimal=True), nullable=False)
    longitude = db.Column(db.Float(asdecimal=True), nullable=False)
    geohash_bit_1 = db.Column(db.String(), nullable=False)
    geohash_bit_2 = db.Column(db.String(), nullable=False)
    geohash_bit_3 = db.Column(db.String(), nullable=False)
    geohash_bit_4 = db.Column(db.String(), nullable=False)
    geohash_bit_5 = db.Column(db.String(), nullable=False)
    geohash_bit_6 = db.Column(db.String(), nullable=False)
    geohash_bit_7 = db.Column(db.String(), nullable=False)
    geohash_bit_8 = db.Column(db.String(), nullable=False)
    geohash_bit_9 = db.Column(db.String(), nullable=False)
    geohash_bit_10 = db.Column(db.String(), nullable=False)
    geohash_bit_11 = db.Column(db.String(), nullable=False)
    geohash_bit_12 = db.Column(db.String(), nullable=False)

    def __repr__(self) -> str:
        return f"<Zipcode {self.zipcode}>"

    @property
    def geohash(self) -> str:
        return "".join([getattr(self, f"geohash_bit_{i}") for i in range(1, 13)])

    @property
    def city(self) -> City:
        return City.query.filter_by(id=self.city_id).one()
