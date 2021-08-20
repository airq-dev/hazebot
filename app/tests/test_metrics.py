import datetime

from airq.lib.clock import now
from airq.models.metrics import Metric
from airq.models.zipcodes import Zipcode
from tests.base import BaseTestCase


class MetricQueryTestCase(BaseTestCase):
    def test_filter_for_deletion(self):
        zipcode = Zipcode.query.first()
        old_metric = Metric(
            zipcode_id=zipcode.id,
            pm25=0,
            humidity=0,
            pm_cf_1=0,
            created_at=now()
            - datetime.timedelta(days=Metric.RETENTION_DAYS, seconds=1),
        )
        new_metric = Metric(
            zipcode_id=zipcode.id,
            pm25=0,
            humidity=0,
            pm_cf_1=0,
            created_at=now() - datetime.timedelta(days=Metric.RETENTION_DAYS),
        )
        self.db.session.add(old_metric)
        self.db.session.add(new_metric)
        self.db.session.commit()

        metric_ids = {
            metric_id
            for (metric_id,) in Metric.query.filter_for_deletion().with_entities(
                Metric.id
            )
        }
        self.assertIn(old_metric.id, metric_ids)
        self.assertNotIn(new_metric.id, metric_ids)
