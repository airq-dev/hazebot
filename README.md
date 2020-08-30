# Airq

Airq allows you to recieve information about the air quality near you simply by sending an SMS. While this is FOSS, it does require a bit of setup if you want to run it yourself: you'll need to setup a Twilio account and then deploy this application somewhere. Changes to the code in the `deploy` directory, and in the `docker-compose` files,  will be neceessary.


# Features

Right now, Airq supports two different air quality APIs as backends: [airnow](https://docs.airnowapi.org/) and [purpleair](https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit?usp=sharing). We are still deciding which API is optimal for our needs, or even if some combinatin of APIs is most useful, so for now we support both.


# Local Setup

To install locally, simply clone this repo. If you want to test with airnow only, you can run `docker-compose up --build`. Then visit `localhost:5000/forecast?zipcode=<YOUR ZIP>` to test. This endpoint returns exactly what you'd see if you sent an SMS to a Twilio callback registered to point at this app.

If you want to test with purpleair, you need to do a bit more work, but not much:
* From the root of this repository, `cd data`.
* `python3 -m venv .venv` to create a virtual environment.
* `source .venv/bin/activate` to activate your virtual environment.
* `python3 -m pip install -r requirements.txt` to install the requirements for building the data source for purpleair.
* `python3 build.py`.

Wait 5 mintes or so — this takes some time. At the end of the build process, you'll have a sqlite database which acts as a static mapping from zipcodes to purpleair sensors, which are then queried in real time by the app. Now run `docker-compose up --build` and test the API by navigating to `http://localhost:5000/feedback?zipcode<YOUR ZIPCODE>&provider=purpleair`.


# Productionizing

This is more complicated. Ping me if you actually want to do this.
