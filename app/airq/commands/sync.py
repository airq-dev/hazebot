import click


@click.option("-g", "--geography")
def sync(geography):
    from airq.tasks import models_sync

    models_sync(bool(geography))
