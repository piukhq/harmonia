import typing as t

import click
import gnupg

import settings
from app import tasks
from app.core import key_manager
from app.core.identify_retry_worker import IdentifyRetryWorker


@click.group()
def cli() -> None:
    pass


@cli.command()
def identify_retry() -> None:
    if settings.DEBUG:
        print("Warning: Running in debug mode. Exceptions will not be handled gracefully!")
    worker = IdentifyRetryWorker()
    worker.run()


@cli.command()
def worker():
    import rq_worker_settings

    tasks.run_worker(rq_worker_settings.QUEUES)


@cli.group()
def keys():
    pass


@keys.command()
@click.argument("slug")
@click.argument("key", type=click.File("wb"))
def read(slug: str, key: t.IO[bytes]):
    """Download the SLUG key from the vault into DIRECTORY"""
    fmt_slug = click.style(slug, fg="cyan", bold=True)
    fmt_path = click.style(key.name, fg="cyan", bold=True)
    click.echo(f"Downloading {fmt_slug} key into {fmt_path}")

    manager = key_manager.KeyManager()
    try:
        key_data = manager.read_key(slug)
    except key_manager.KeyDoesNotExistError as ex:
        fmt_err = click.style(str(ex), fg="red", bold=True)
        click.echo(f"Key manager raised an error: {fmt_err}")

    key.write(key_data)


@keys.command()
@click.argument("slug")
@click.argument("key", type=click.File("rb"))
def write(slug: str, key: t.IO[bytes]):
    """Upload KEY to the vault as SLUG"""
    fmt_slug = click.style(slug, fg="cyan", bold=True)
    fmt_path = click.style(key.name, fg="cyan", bold=True)
    click.echo(f"Uploading {fmt_path} to vault as {fmt_slug}.")

    manager = key_manager.KeyManager()
    manager.write_key(slug, key.read())


@keys.command()
@click.argument("email")
@click.argument("passphrase")
def gen(email: str, passphrase: str):
    """Generate a new keypair for EMAIL and dump the secret key to stdout"""
    gpg = gnupg.GPG(**settings.GPG_ARGS)
    input_data = gpg.gen_key_input(name_email=email, passphrase=passphrase)
    key = gpg.gen_key(input_data)
    priv_key_asc = gpg.export_keys(key.fingerprint, secret=True, passphrase=passphrase)
    click.echo(priv_key_asc)


@keys.command()
def list():
    """List all keys in the keychain"""
    gpg = gnupg.GPG(**settings.GPG_ARGS)
    for key in gpg.list_keys():
        print(f"[{key['keyid']}] {key['uids'][0]}")


if __name__ == "__main__":
    cli()
