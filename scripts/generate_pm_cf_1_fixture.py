import json
import random


def main():
    # First open existing fixture data
    # We will generate random-ish pm_cf_1 data from it

    with open("app/tests/fixtures/purpleair/purpleair.json") as f:
        data = json.load(f)
    fields = data["fields"]
    raw = data["data"]
    data = [dict(zip(fields, d)) for d in raw]
    pm_cf_1_data = []
    for d in data:
        s_id = d["sensor_index"]
        pm25 = d["pm2.5"]
        if isinstance(pm25, float):
            pm_cf_1 = pm25 + round(random.random(), ndigits=2) * 5
            pm_cf_1_data.append([s_id, pm_cf_1])
    with open("app/tests/fixtures/purpleair/pm_cf_1.json", "w") as f:
        json.dump({"data": pm_cf_1_data, "fields": ["ID", "pm_cf_1"]}, f)


if __name__ == "__main__":
    main()
