# Contributing

We're thrilled you want to contribute to Hazebot. Please check out our [issues](https://github.com/airq-dev/hazebot/issues) to get a sense of the projects we're focusing on. If you want to work on something which is not in the issues section, please open a new issue or visit us on our [Slack](https://join.slack.com/t/hazebot/shared_invite/zt-hoogtwy8-9yeYFKyg0MRCtyC9US0k3Q).

The following is a technical overview of how to make contributions to hazebot. We cover:
1. [Getting setup for local development](#Setting-up-local-development)
2. [Running tests](#Running-Tests)
3. [Opening a PR](#Opening-a-PR)
4. [Using the debugger](#Debugging)
5. [Accessing the database](#Accessing-the-Database)
6. [Changing the database schema](#Schema-Changes)

You should also read our [architecture docs](architecture.md#Architecture) for a high-level overview of how Hazebot works.

## Setting up local development

To run Hazebot locally you'll need to obtain a read key for the Purpleair API. Please request one from contact@purpleair.com. (Note: a good project could be to provide fake data for local development. Then this step wouldn't be necessary.)

Once you have your read key, clone this repo. Then create a new `.env.dev.secrets` file (this will be gitignored) and add the following line:

```
PURPLEAIR_API_KEY=<your read key>
```

Then run `docker-compose up --build`. Once the app is running, if this is the first time you've built Hazebot locally, run `docker-compose exec app flask sync --geography`. This runs the synchronization process described [here](architecture.md#Synchronizing-Data) to populate your database.

You can then test the API by navigating to `http://localhost:5000/test?command=<YOUR ZIPCODE>`. The `/test` endpoint returns the same message you'd get if you sent a text to a callback registered with Twilio to point at the `/sms_reply` endpoint exposed by this app.

## Running tests

Run all tests with `./test.sh` or a specific test with `./test.sh <tests.test_module>`.

This script will start a separate docker cluster (isolated from the development cluster) using fixtures taken from a subset of Purpleair and GeoNames data near Portland, Oregon. This "static" data (e.g., zipcodes and cities) is not deleted between test runs. Instead, it is rebuilt as part of the test suite (specifically, during the `test_sync` case). This makes it possible to run the test suite without rebuilding this data before each test, speeding up test time substantially. And any change you make to the sync process will still be exercised when `test_sync` runs.

## Adding, updating or removing strings

If you add, update or remove strings which are visible to non-admin users, you'll need to make sure to include Spanish translations. To do this, follow the (unfortunately somewhat laborious) process laid out in the [translations](translations.md) docs. We're trying to make this process easier!

## Opening a PR

Before you open a PR, please do the following:
* Run `black .` from the root of this repo and ensure it exits without error. [Black](https://github.com/psf/black) is a code formatter which will ensure your code-style is compliant with the rest of this repository. You can install Black with `pip install 'black==20.8b1'`.
* Run `mypy app` from the root of this repo and ensure it exits without error. [Mypy](http://mypy-lang.org/) is a static analysis tool which helps ensure that code is type-safe. You can install Mypy with `pip install mypy`.
* Ensure tests pass (you can run the whole suite with `./test.sh`).
* If you're making a non-trivial change, please add or update test cases to cover it.

## Debugging

It is possible to debug during development by attaching to the running docker container. First, get the app container id:

```
$ docker container ls
CONTAINER ID        IMAGE                 COMMAND                  CREATED             STATUS              PORTS                              NAMES
0f8dcbf12ae0        airq_app              "/home/app/app/entry…"   29 minutes ago      Up 29 minutes       0.0.0.0:5000->5000/tcp             airq_app_1
```

Then, attach to the app container:

```
$ docker attach 0f8dcbf12ae0
```

The process should hang. Now open your editor and add a breakpoint using [pdb](https://docs.python.org/3/library/pdb.html): `import pdb; pdb.set_trace()`. When Python hits the breakpoint, it will start a debugger session in the shell attached to the app container.

## Accessing the database

You can directly query Postgres via Docker while the app is running. Run:

```
docker-compose exec db /bin/sh  # gets you a command line in the container
psql --user postgres  # logs you into the database
```

## Schema changes

We use [Alembic](https://alembic.sqlalchemy.org/en/latest/) via the [Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/) plugin to manage the Hazebot database schema. If you'd like to make a change to a model, add a new model, or alter the database in some other way, you will need to make a migration. The Flask-Migrate docs are a great place to start, but a brief overview is provided here.

1. Fire up docker per the instruction in [Local Setup](#Local_Setup)
2. Make the change to your model; e.g., adding a new column.
3. Run `docker-compose exec app flask db migrate -m "<some descriptive message>"`. This will generate a new migration file in the `migrations` directory.
4. If you need to backfill data via a custom script, you can extend your migration script with a custom data migration. See `app/migrations/versions/549f168d1eaf_add_zipcode_id_to_request.py` for an example.
4. Run `docker-compose web flask upgrade --sql`.
5. Check that the resulting SQL looks good. Note that the `--sql` options outputs SQL for all migrations, not just yours. But you only need to look at the SQL for the migration your created.
6. Run `docker-compose web flask upgrade` to run the migration.
7. Bring down your test containers with `./test.sh -d`.
8. Bring them back up with `./test.sh`. This will apply the migrations to the test database.
