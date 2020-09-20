# Hazebot

Building the 411 for air quality in the United States: a texting platform accessible to all, that provides actionable local information to protect your and your community. You can also visit us at [hazebot.org](https://www.hazebot.org).

![Build](https://github.com/ianhoffman/airq/workflows/Deploy/badge.svg?branch=master)

## Features

To use Hazebot, simply text your zipcode to 26AQISAFE2 or (262) 747-2332, and we will send you an alert when the air quality in your zipcode changes [categories](https://cfpub.epa.gov/airnow/index.cfm?action=aqibasics.aqi). Hazebot sends each user no more than one alert every hour, and only between the hours of 8AM and 9PM.

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
4. We loop over each zipcode in the `zipcodes` table and calculate the current average reading for that zipcode from the most up-to-date data in the `sensors` table. We update the `zipcodes` table with this data.
5. We loop over each row in the `clients` table and alert all clients which qualify.

Once per day, at 12 AM UTC, the worker synchronizes the `zipcodes` table with the latest data from [GeoNames](https://www.geonames.org/) before running the synchronization process described above.

## Contributing

### Local Setup

Clone this repo and run `docker-compose up --build`. Once the app is running, if this is the first time you've built Hazebot locally, run `docker-compose exec app flask sync --geography`. This runs the synchronization process described above to populate your database.

You can then test the API by navigating to `http://localhost:5000/test?command=<YOUR ZIPCODE>`. The `/test` endpoint returns the same message you'd get if you sent a text to a callback registered with Twilio to point at the `/sms_reply` endpoint exposed by this app.

### Running Tests

Run all tests with `./test.sh` or a specific test with `./test.sh <tests.test_module>`.

This script will start a separate docker cluster (isolated from the development cluster) using fixtures taken from a subset of Purpleair and GeoNames data near Portland, Oregon. This "static" data (e.g., zipcodes and cities) is not deleted between test runs. Instead, it is rebuilt as part of the test suite (specifically, during the `test_sync` case). This makes it possible to run the test suite without rebuilding this data before each test, speeding up test time substantially. And any change you make to the sync process will still be exercised when `test_sync` runs.

### Opening a PR

Before you open a PR, please do the following:
* Run `black .` from the root of this repo and ensure it exits without error. [Black](https://github.com/psf/black) is a code formatter which will ensure your code-style is compliant with the rest of this repository. You can install Black with `pip install 'black==19.10b0'`.
* Run `mypy app` from the root of this repo and ensure it exits without error. [Mypy](http://mypy-lang.org/) is a static analysis tool which helps ensure that code is type-safe. You can install Mypy with `pip install mypy`.
* Ensure tests pass (you can run the whole suite with `./test.sh`).
* If you're making a non-trivial change, please add or update test cases to cover it.

### Debugging

It is possible to debug during development by attaching to the running docker container. First, get the app container id:

```
ianhoffman|master:~/github/airq$ docker container ls
CONTAINER ID        IMAGE                 COMMAND                  CREATED             STATUS              PORTS                              NAMES
0f8dcbf12ae0        airq_app              "/home/app/app/entry…"   29 minutes ago      Up 29 minutes       0.0.0.0:5000->5000/tcp             airq_app_1
```

Then, attach to the app container:

```
ianhoffman|master:~/github/airq$ docker attach 0f8dcbf12ae0
```

The process should hang. Now open your editor and add a breakpoint using [pdb](https://docs.python.org/3/library/pdb.html): `import pdb; pdb.set_trace()`. When Python hits the breakpoint, it will start a debugger session in the shell attached to the app container.

### Accessing the Database

You can directly query Postgres via Docker while the app is running. Run:

```
docker-compose db /bin/sh  # gets you a command line in the container
psql --user postgres  # logs you into the database
```
