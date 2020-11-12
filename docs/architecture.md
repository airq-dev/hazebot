# Architecture

Hazebot is built on top of [PurpleAir](https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit?usp=sharing) sensors, which provide much more up-to-date readings than the EPA does at the cost of accuracy. As such, Hazebot aggregates readings from many nearby sensors when estimating the air quality in your zipcode.

Since PurpleAir sensors update with a granularity of around ten minutes (and because PurpleAir rate-limits heavily), we use a queue-based architecture in which the application server reads air quality metrics directly from the database, and the database is kept in-sync with PurpleAir by a worker. Specifically, we run a Celery worker which synchronizes several tables against PurpleAir readings every ten minutes. We then run a Flask application which queries these tables to serve incoming requests.

## Synchronizing Data

The synchronization process is one of the most complex parts of Hazebot's architecture. It is a multi-phase process which proceeds as follows:

1. All current sensor readings are retrieved from PurpleAir.
2. The `sensors` table is updated with these readings. Any previously unseen sensors are inserted into the `sensors` table.
3. The relationship table between sensors and zipcodes, `sensors_zipcodes`, is updated with the latest sensor locations. Usually there's not much to do here, but when a new sensor comes online or when one moves we use [Geohashing](https://en.wikipedia.org/wiki/Geohash) to create associations between it and all zipcodes within 25 kilometers.
4. We loop over each zipcode in the `zipcodes` table and calculate the current average reading for that zipcode from the most up-to-date data in the `sensors` table. We update the `zipcodes` table with this data.
5. We loop over each row in the `clients` table and alert all clients which qualify.

Once per day, at 12 AM UTC, the worker synchronizes the `zipcodes` table with the latest data from [GeoNames](https://www.geonames.org/) before running the synchronization process described above.
