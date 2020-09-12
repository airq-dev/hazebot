from airq.config import db


class City(db.Model):  # type: ignore
    __tablename__ = "cities"

    id = db.Column(db.Integer(), nullable=False, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    state_code = db.Column(db.String(2), nullable=False)

    __table_args__ = (
        db.Index("_name_state_code_index", "name", "state_code", unique=True,),
    )
