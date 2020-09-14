import datetime
import typing

from airq.config import db


class Subscription(db.Model):  # type: ignore
    __tablename__ = "subscriptions"

    zipcode_id = db.Column(
        db.Integer(),
        db.ForeignKey("zipcodes.id", name="subscription_zipcode_id_fkey"),
        nullable=False,
        primary_key=True,
    )
    client_id = db.Column(
        db.Integer(),
        db.ForeignKey("clients.id", name="subscription_client_id_fkey"),
        nullable=False,
        primary_key=True,
    )
    created_at = db.Column(db.Integer(), nullable=False)
    disabled_at = db.Column(db.Integer(), default=0, nullable=False, index=True)
    last_executed_at = db.Column(db.Integer(), default=0, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Subscription {self.zipcode_id} {self.client_id}>"

    @property
    def is_enabled(self) -> bool:
        return not self.is_disabled

    @property
    def is_disabled(self) -> bool:
        return bool(self.disabled_at)

    def enable(self):
        self.disabled_at = 0
        db.session.commit()

    def disable(self):
        self.disabled_at = datetime.datetime.now().timestamp()
        db.session.commit()

    @classmethod
    def get_available_to_send(cls) -> typing.List["Subscription"]:
        cutoff = datetime.datetime.now().timestamp() - (60 * 60)
        return cls.query.filter(Subscription.last_executed_at < cutoff).filter(
            Subscription.disabled_at == 0
        )

    @classmethod
    def get_or_create(
        cls, client_id: int, zipcode_id: int
    ) -> typing.Tuple["Subscription", bool]:
        subscription = cls.query.filter_by(
            client_id=client_id, zipcode_id=zipcode_id
        ).first()
        if subscription is None:
            subscription = cls(
                client_id=client_id,
                zipcode_id=zipcode_id,
                created_at=datetime.datetime.now().timestamp(),
            )
            db.session.add(subscription)
            db.session.commit()
            was_created = True
        else:
            was_created = False
        return subscription, was_created
