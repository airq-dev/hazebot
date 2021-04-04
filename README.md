# Hazebot

Building the 411 for air quality in the United States: a texting platform accessible to all, that provides actionable local information to protect your and your community. Simply text your zipcode to (262) 747-2332 to receive timely alerts when the air quality near you changes.

You can also visit us at [hazebot.org](https://www.hazebot.org). Hazebot is built on top of data from [PurpleAir](https://www2.purpleair.com/).

![Build](https://github.com/ianhoffman/airq/workflows/Deploy/badge.svg?branch=master)

## Contributing

Contributions are very welcome. Please see a detailed guide to contributing [here](docs/contributing.md#Contributing). You can always reach us on our [Slack](https://join.slack.com/t/hazebot/shared_invite/zt-hoogtwy8-9yeYFKyg0MRCtyC9US0k3Q) if you'd like to get involved.

## Features

To use Hazebot, simply text your zipcode to 26AQISAFE2 or (262) 747-2332, and we will send you an alert when the air quality in your zipcode changes [categories](https://cfpub.epa.gov/airnow/index.cfm?action=aqibasics.aqi). Hazebot sends each user no more than one alert every two hours, and only between the hours of 8AM and 9PM. You can also customize your alerting preferences via SMS.

We also support several SMS "commands", the full list of which can be viewed in the Hazebot menu (by texting "M" to Hazebot).

If interested, you can read about the technical implementation of Hazebot in our [architecture docs](docs/architecture.md).
