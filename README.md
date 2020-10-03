# Hazebot

Building the 411 for air quality in the United States: a texting platform accessible to all, that provides actionable local information to protect your and your community. Simply text your zipcode to (262) 747-2332 to receive timely alerts when the air quality nea you changes.

You can also visit us at [hazebot.org](https://www.hazebot.org).

![Build](https://github.com/ianhoffman/airq/workflows/Deploy/badge.svg?branch=master)

## Contributing

Contributions are very welcome. Please see a detailed guide to contributing [here](docs/contributing.md#Contributing). You can always reach us on our [Slack channel](https://join.slack.com/t/hazebot/shared_invite/zt-hoogtwy8-9yeYFKyg0MRCtyC9US0k3Q) if you'd like to get involved.

## Features

To use Hazebot, simply text your zipcode to 26AQISAFE2 or (262) 747-2332, and we will send you an alert when the air quality in your zipcode changes [categories](https://cfpub.epa.gov/airnow/index.cfm?action=aqibasics.aqi). Hazebot sends each user no more than one alert every two hours, and only between the hours of 8AM and 9PM.

We also support several SMS "commands":
* `1`: Get details about the air quality in your zipcode, and recommendations of nearby areas with healthier air.
* `2`: Get up-to-date metrics for your zipcode, without waiting for an alert.
* `3`: Get info about hazebot.
* `m`: View the hazebot menu (basically commands `1`, `2`, and `3`).
* `u`: Unsubscribe from alerts.

If interested, you can read about the technical implementation of Hazebot in our [architecture docs](docs/architecture.md).