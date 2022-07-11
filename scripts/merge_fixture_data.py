import json
from pathlib import PurePath


def merge_fixture_data():
    with open("../app/tests/fixtures/purpleair/pm_cf_1.json") as f:
        pm_cf_1_readings = dict(json.load(f)["data"])
    with open("../app/tests/fixtures/purpleair/purpleair.json") as f:
        purpleair_readings = json.load(f)
    purpleair_readings["fields"].append("pm2.5_cf_1")
    sensors = {row[0]: row for row in purpleair_readings["data"]}
    new = []
    for sensor_id, data in sensors.items():
        pm_cf_1 = pm_cf_1_readings.get(sensor_id)
        if pm_cf_1 is not None:
            data.append(pm_cf_1)
            new.append(data)
    purpleair_readings["data"] = new
    with open("../app/tests/fixtures/purpleair/purpleair2.json", "w") as f:
        json.dump(purpleair_readings, f)


if __name__ == "__main__":
    merge_fixture_data()
