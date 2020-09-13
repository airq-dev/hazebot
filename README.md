# Hazebot - TEXT your ZIP to 26AQISAFE2 for local, up-to-date air quality.

Building the 411 for air quality in the United States: a texting platform accessible to all, that provides actionable local information about air quality to protect your and your community. 

https://www.hazebot.org/


![Build](https://github.com/ianhoffman/airq/workflows/Deploy/badge.svg?branch=master)

Hazebot allows you to recieve information about the air quality near you simply by sending an SMS. While this is FOSS, it does require a bit of setup if you want to run it yourself: you'll need to setup a Twilio account and then deploy this application somewhere. Currently airq is deployed to Amazon ECS, but it could be deployed elsewhere — either way, you'll need to setup the necessary infrastructure.


## Features

Hazebot aggregates sensor readings from nearby [Purpleair](https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit?usp=sharing) sensors. These sensors are updated every 10 minutes so the results should be fairly accurate, generally. 

Text a zipcode to 26AQISAFE2 or (262) 747-2332 for aggregate pm2.5 measures and recommendations for places near you with better AQI. 


## Architecture

Since Purpleair rate-limits heavily and their sensors update with a granularity of around 10 minutes, we run a Celery job every ten minutes which pulls down all sensor data and inserts it into the `sensors` table in Postgres. We then maintain a mapping in the `sensors_zipcodes` table from sensors to zipcodes, and so, given a zipcode, we can easily find all nearby sensors and query their readings without an API call. 

Once per day, at midnight, we also synchronize all zipcode and city information with Geonames.

Thus the app has two main components: a worker, which handles synchronizing with Purpleair / Geonames and updating Postgres, and an application server, which queries Postgres for readings.

## TODOs

* Email logging for alerts/errors.
* Come up with behavior recs for air quality based on pm2.5 
* Write tests (!).
* Push notifications.
* Slack integration. 


## Contributing

Follow the instructions in the [Local Setup](#local-setup) section. PRs are happily accepted.

You'll want to install [black](https://github.com/psf/black): `pip install 'black==19.10b0'`. Before committing your changes, run `black .` from the repository root to ensure consistent formatting.

You'll also want to install the latest version of [mypy](http://mypy-lang.org/) and run `mypy app` from the root of this repository before committing.


### Local Setup

To run `airq` locally, you'll need a set of AWS credentials with full SQS permissions (we should consider using redis for local development so this isn't necessary). Provision these for yourself and put them in a file called `.env.dev.secrets` at the root of this repo, as follows:

```
AWS_ACCESS_KEY_ID=<your access key>
AWS_SECRET_ACCESS_KEY=<your secret key>
```

Do not commit this file! (It's in the .gitignore by default.) 

Once you've done that, run `docker-compose up --build`. Then run `flask sync --geography` to build all the tables — this will take some time. Once this is done, you can test the API by navigating to `http://localhost:5000/quality?zipcode<YOUR ZIPCODE>`.

The `/quality` endpoint returns the same message you'd get if you sent a text to a callback registered with Twilio to point at the `/sms_reply` endpoint exposed by this app.
