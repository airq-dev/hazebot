# Airq

![Build](https://github.com/ianhoffman/airq/workflows/Deploy/badge.svg?branch=master)

Airq allows you to recieve information about the air quality near you simply by sending an SMS. While this is FOSS, it does require a bit of setup if you want to run it yourself: you'll need to setup a Twilio account and then deploy this application somewhere. Currently airq is deployed to Amazon ECS, but it could be deployed elsewhere — either way, you'll need to setup the necessary infrastructure.


## Features

Right now, Airq returns reading from two different air quality APIs: [airnow](https://docs.airnowapi.org/) and [purpleair](https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit?usp=sharing). We are still deciding which combination of APIs is most optimal for our needs, or if just using one API is sufficient.


## TODOs

* Register a domain and setup SES to email admins whenever Flask throws an exception.
* Determine which air quality data should actually be public-facing.
* Understand why there are large differences in the air quality as calculated by purpleair and airnow.
* Create a task worker (somewhere? EC2?) to send alerts when air quality changes by a certain amount.
* As a prerequisite to the above task, setup a database in RDS to store phone numbers and zipcodes.
* Have the task worker rebuild the purpleair database once per day and push it to github, triggering a deploy.


## Contributing

Follow the instructions in the [Local Setup](#local-setup) section. PRs are happily accepted.

### Local Setup

To install locally, clone this repo. Then build the data for pupleair:

* From the root of this repository, `cd data`.
* `python3 -m venv .venv` to create a virtual environment.
* `source .venv/bin/activate` to activate your virtual environment.
* `python3 -m pip install -r requirements.txt` to install the requirements for building the data source for purpleair.
* `python3 build.py`.

Wait 5 mintes or so — this takes some time. At the end of the build process, you'll have a sqlite database which acts as a static mapping from zipcodes to purpleair sensors, which are then queried in real time by the app. 

Now run `docker-compose up --build` and test the API by navigating to `http://localhost:5000/quality?zipcode<YOUR ZIPCODE>`. This will return data from both purpleair and airnow. If you want data from just one provider, append `&provider=<purpleair|airnow>` to your request. 

The `/quality` endpoint returns the same message you'd get if you sent a text to a callback registered with Twilio to point at the `/sms_reply` endpoint exposed by this app.

Obviously it will be necessary to rebuild the purpleair database every once in awhile as purpleair sensors do go offline, come online, and move around. An eventual todo is to create a cron which does this for us.