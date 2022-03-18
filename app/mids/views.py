import csv
import string
import typing as t
from functools import lru_cache

import werkzeug
from flask import Blueprint, request
from sqlalchemy.dialects.postgresql import insert

import settings
from app import db, models, reporting
from app.api.auth import auth_decorator
from app.api.utils import view_session

api = Blueprint("mids_api", __name__, url_prefix=f"{settings.URL_PREFIX}/mids")
requires_auth = auth_decorator()
log = reporting.get_logger("mids-api")


ResponseType = t.Tuple[t.Dict, int]


class CSVDialect(csv.Dialect):
    delimiter = ","
    escapechar = '"'
    lineterminator = "\n"
    quoting = csv.QUOTE_NONE


@lru_cache(128)
def get_loyalty_scheme(slug, *, session: db.Session):
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, session=session, slug=slug)
    return loyalty_scheme


@lru_cache(128)
def get_payment_provider(slug, *, session: db.Session):
    payment_provider, _ = db.get_or_create(models.PaymentProvider, session=session, slug=slug)
    return payment_provider


def create_merchant_identifier_fields(
    payment_provider_slug,
    mid,
    location_id,
    merchant_internal_id,
    loyalty_scheme_slug,
    location,
    postcode,
    *,
    session: db.Session,
) -> dict:
    loyalty_scheme = get_loyalty_scheme(loyalty_scheme_slug, session=session)
    payment_provider = get_payment_provider(payment_provider_slug, session=session)

    return dict(
        mid=mid,
        location_id=location_id if location_id else None,
        merchant_internal_id=merchant_internal_id if merchant_internal_id else None,
        loyalty_scheme_id=loyalty_scheme.id,
        payment_provider_id=payment_provider.id,
        location=location,
        postcode=postcode,
    )


def _get_first_character(file_storage: werkzeug.datastructures.FileStorage) -> str:
    # the `line for line in ...` is required since FileStorage isn't a proper iterable
    char = next(line for line in file_storage).decode()[0]
    file_storage.stream.seek(0)
    return char


def add_mids_from_csv(file_storage: werkzeug.datastructures.FileStorage, *, session: db.Session) -> t.Tuple[int, int]:
    mark = _get_first_character(file_storage)
    if mark not in string.printable:
        raise ValueError(
            "File starts with an invalid character. Ensure the file has been saved in UTF-8 format with no BOM."
        )

    reader = csv.reader((line.decode() for line in file_storage), dialect=CSVDialect())

    log.debug("Processing MIDs...")

    merchant_identifiers_fields = []
    for line, row in enumerate(reader):
        row = [value.strip() for value in row]
        try:
            (
                payment_provider_slug,
                mid,
                loyalty_scheme_slug,
                location_id,
                merchant_internal_id,
                loyalty_scheme_name,
                location,
                postcode,
                action,
            ) = row
        except ValueError as ex:
            raise ValueError(f"Expected 8 items at line {line} of file, got {len(row)}") from ex

        if action.lower() != "a":
            continue

        merchant_identifier_fields = create_merchant_identifier_fields(
            payment_provider_slug,
            mid,
            location_id,
            merchant_internal_id,
            loyalty_scheme_slug,
            location,
            postcode,
            session=session,
        )
        merchant_identifiers_fields.append(merchant_identifier_fields)

    n_mids_in_file = len(merchant_identifiers_fields)

    log.debug(f'Importing {n_mids_in_file} MIDs from "{file_storage.name}"')

    def insert_mids():
        db.engine.execute(
            insert(models.MerchantIdentifier.__table__).values(merchant_identifiers_fields).on_conflict_do_nothing()
        )
        session.commit()

    mids_table_before = db.run_query(
        lambda: session.query(models.MerchantIdentifier).count(),
        session=session,
        read_only=True,
        description="count MIDs before import",
    )
    db.run_query(insert_mids, session=session, description="import MIDs")
    mids_table_after = db.run_query(
        lambda: session.query(models.MerchantIdentifier).count(),
        session=session,
        read_only=True,
        description="count MIDs after import",
    )

    return n_mids_in_file, mids_table_after - mids_table_before


@api.route("/", methods=["POST"])
@requires_auth(auth_scopes="mids:write")
@view_session
def import_mids(*, session: db.Session) -> ResponseType:
    """
    Import MIDs
    ---
    post:
        description: Upload MIDs CSV file
        responses:
            200:
                description: "Import was successful"
    """
    imported: t.List[dict] = []
    failed: t.List[dict] = []

    def fail(filepath: str, reason: str) -> None:
        failed.append({"file": filepath, "reason": reason})

    for filepath, file_storage in request.files.items():
        log.debug(f'Attempting to import MIDs file "{filepath}"')
        if file_storage.content_type != "text/csv":
            fail(filepath, f"Expected file content type text/csv, got {file_storage.content_type}")
            continue
        try:
            n_mids_in_file, n_mids_imported = add_mids_from_csv(file_storage, session=session)
        except Exception as ex:
            error_message = f"{type(ex).__name__}: {ex}"
            if len(error_message) > 250:
                error_message = f"{error_message[:248]} …"
            fail(filepath, error_message)
        else:
            imported.append({"file": filepath, "in_file": n_mids_in_file, "imported": n_mids_imported})

    # clear the caches to avoid getting cached objects from old sessions
    get_loyalty_scheme.cache_clear()
    get_payment_provider.cache_clear()

    return {"imported": imported, "failed": failed}, 200
