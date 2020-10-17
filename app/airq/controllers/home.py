import json
from flask import render_template

from airq.models.sensors import Sensor

def home() -> str:
    points = {
        sensor_id: {
            "latitude": latitude,
            "longitude": longitude,
        } for sensor_id, latitude, longitude
        in Sensor.query.with_entities(Sensor.id, Sensor.latitude, Sensor.longitude).all()
    }
    return render_template("home.html", points=json.dumps(points))