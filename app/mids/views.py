import csv
import typing as t
from functools import lru_cache

from sqlalchemy.dialects.postgresql import insert
from flask import Blueprint, request, jsonify
import werkzeug

from app import models, db, reporting
import settings


api = Blueprint("mids_api", __name__, url_prefix=f"{settings.URL_PREFIX}/mids")

log = reporting.get_logger("mids-api")


ResponseType = t.Tuple[t.Dict, int]


class CSVDialect(csv.Dialect):
    delimiter = ","
    escapechar = '"'
    lineterminator = "\n"
    quoting = csv.QUOTE_NONE


@lru_cache(128)
def get_loyalty_scheme(slug):
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug=slug)
    return loyalty_scheme


@lru_cache(128)
def get_payment_provider(slug):
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug=slug)
    return payment_provider


def create_mid_from_values(payment_provider_slug, mid, loyalty_scheme_slug, location, postcode) -> dict:
    loyalty_scheme = get_loyalty_scheme(loyalty_scheme_slug)
    payment_provider = get_payment_provider(payment_provider_slug)

    return dict(
        mid=mid,
        loyalty_scheme_id=loyalty_scheme.id,
        payment_provider_id=payment_provider.id,
        location=location,
        postcode=postcode,
    )


def add_mids_from_csv(file_storage: werkzeug.datastructures.FileStorage) -> None:
    reader = csv.reader((line.decode() for line in file_storage), dialect=CSVDialect())

    log.debug("Processing MIDs...")

    mids = []
    for line, row in enumerate(reader):
        try:
            payment_provider_slug, mid, loyalty_scheme_slug, loyalty_scheme_name, location, postcode, action = row
        except ValueError as ex:
            raise ValueError(f"Expected 7 items at line {line} of file, got {len(row)}") from ex

        if action.lower() != "a":
            continue

        mid = create_mid_from_values(payment_provider_slug, mid, loyalty_scheme_slug, location, postcode)
        mids.append(mid)

    n_mids_in_file = len(mids)

    log.debug(f'Importing {n_mids_in_file} MIDs from "{file_storage.name}"')

    def insert_mids():
        db.engine.execute(insert(models.MerchantIdentifier.__table__).values(mids).on_conflict_do_nothing())
        db.session.commit()

    mids_table_before = db.run_query(lambda: db.session.query(models.MerchantIdentifier).count())
    db.run_query(insert_mids)
    mids_table_after = db.run_query(lambda: db.session.query(models.MerchantIdentifier).count())

    return n_mids_in_file, mids_table_after - mids_table_before


@api.route("/", methods=["POST"])
def import_mids() -> ResponseType:
    """
    Import MIDs
    ---
    post:
        description: Upload MIDs CSV file
        responses:
            200:
                description: "Import was successful"
    """
    imported: t.List[str] = []
    failed: t.List[t.Dict[str, str]] = []

    def fail(filepath: str, reason: str) -> None:
        failed.append({"file": filepath, "reason": reason})

    for filepath, file_storage in request.files.items():
        log.debug(f'Attempting to import MIDs file "{filepath}"')
        if file_storage.content_type != "text/csv":
            fail(filepath, f"Expected file content type text/csv, got {file_storage.content_type}")
            continue
        try:
            n_mids_in_file, n_mids_imported = add_mids_from_csv(file_storage)
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

    return jsonify({"imported": imported, "failed": failed}), 200
