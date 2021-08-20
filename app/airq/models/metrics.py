from datetime import timedelta

from flask_sqlalchemy import BaseQuery

from airq.config import db
from airq.lib.clock import now


class MetricQuery(BaseQuery):
    def filter_for_deletion(self) -> "MetricQuery":
        return self.filter(
            Metric.created_at < now() - timedelta(days=Metric.RETENTION_DAYS)
        )


class Metric(db.Model):  # type: ignore
    __tablename__ = "metrics"

    query_class = MetricQuery

    id = db.Column(db.Integer(), primary_key=True)
    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="metrics_zipcode_id_fkey"),
        nullable=False,
    )

    pm25 = db.Column(db.Float(), nullable=False)
    humidity = db.Column(db.Float(), nullable=False)
    pm_cf_1 = db.Column(db.Float(), nullable=False)
    details = db.Column(db.JSON(), nullable=False, default="{}")

    created_at = db.Column(
        db.TIMESTAMP(timezone=True), default=now, index=True, nullable=False
    )

    RETENTION_DAYS = 3
