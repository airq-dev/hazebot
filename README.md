# Hazebot - TEXT your ZIP to 26AQISAFE2 for local, up-to-date air quality.

<<<<<<< HEAD
Building the 411 for air quality in the United States: a texting platform accessible to all, that provides actionable local information protect your and your community.
=======
Building the 411 for air quality in the United States: a texting platform accessible to all, that provides actionable local information protect your and your community. You can also visit us at [hazebot.org](www.hazebot.org).
>>>>>>> master

![Build](https://github.com/ianhoffman/airq/workflows/Deploy/badge.svg?branch=master)

## Features

To use Hazebot, simply text your zipcode to 26AQISAFE2 or (262) 747-2332, and we will send you an alert when the air quality in your zipcode changes [categories](https://cfpub.epa.gov/airnow/index.cfm?action=aqibasics.aqi). Hazebot sends each user no more than one alert every three hours, and only between the hours of 8AM and 9PM, so (we hope) this won't feel spammy.

We also support several SMS "commands":
* `1`: Get details about the air quality in your zipcode, and recommendations of nearby areas with healthier air.
* `2`: Get up-to-date metrics for your zipcode, without waiting for an alert.
* `3`: Get info about hazebot.
* `m`: View the hazebot menu (basically commands `1`, `2`, and `3`).
* `u`: Unsubscribe from alerts.

## Architecture

Hazebot is built on top of [PurpleAir](https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit?usp=sharing) sensors, which provide much more up-to-date readings than the EPA does at the cost of accuracy. As such, Hazebot aggregates readings from many nearby sensors when estimating the air quality in your zipcode.

Since PurpleAir sensors update with a granularity of around ten minutes (and because PurpleAir rate-limits heavily), we use a queue-based architecture in which the application server reads air quality metrics directly from the database, and the database is kept in-sync with PurpleAir by a worker. Specifically, we run a Celery worker which synchronizes several tables against PurpleAir readings every ten minutes. We then run a Flask application which queries these tables to serve incoming requests.

### Synchronizing Data

The synchronization process is one of the most complex parts of Hazebot's architecture. It is a multi-phase process which proceeds as follows:

1. All current sensor readings are retrieved from PurpleAir.
2. The `sensors` table is updated with these readings. Any previously unseen sensors are insterted into the `sensors` table.
3. The relationship table between sensors and zipcodes, `sensors_zipcodes`, is updated with the latest sensor locations. Usually there's not much to do here, but when a new sensor comes online or when one moves we use [Geohashing](https://en.wikipedia.org/wiki/Geohash) to create associations between it and all zipcodes within 25 kilometers.
4. We loop over each zipcode in the `zipcodes` table and calculate the current average reading for that zipcode from the most up-to-date data in the `sensors` table. We insert these metrics in the `metrics` table, which aggregates historical per-zipcode data going back two hours.
5. We loop over each row in the `subscriptions` table and alert all users who qualify.

Once per day, at 12 AM UTC, the worker synchronizes the `zipcodes` table with the latest data from [GeoNames](https://www.geonames.org/) before running the synchronization process described above.

## Contributing

<<<<<<< HEAD
Clone this repo and run `docker-compose up --build`. Once the app is running, if this is the first time you've built Hazebot locally, run `docker-compose exec app flask sync --geography`. This runs the synchronization process described above to populate your database.
=======
Clone this repo and run `docker-compose up --build`. Once the app is running, if this is the first time you've built Hazebot locally, run `docker compose exec app flask sync --geography`. This runs the synchronization process described above to populate your database.
>>>>>>> master

You can then test the API by navigating to `http://localhost:5000/quality?zipcode<YOUR ZIPCODE>`. The `/quality` endpoint returns the same message you'd get if you sent a text to a callback registered with Twilio to point at the `/sms_reply` endpoint exposed by this app.

Next, install [black](https://github.com/psf/black) and [mypy](http://mypy-lang.org/):

```
pip install 'black==19.10b0'
pip install mypy
```

Before opening a PR, run `black .` and `mypy app` from the root of this repository and ensure that both exit cleanly (CI will fail otherwise).
