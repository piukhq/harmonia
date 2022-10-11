import csv
import string
import typing as t
from functools import lru_cache

import marshmallow
import werkzeug
from flask import Blueprint, request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import tuple_

import settings
from app import db, models, reporting
from app.api.auth import auth_decorator, requires_service_auth
from app.api.utils import view_session
from app.mids import schemas

api = Blueprint("identifiers_api", __name__, url_prefix=f"{settings.URL_PREFIX}/identifiers")
requires_auth = auth_decorator()
log = reporting.get_logger("identifiers-api")


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


def validate_identifier_type(identifier_type):
    if identifier_type is None:
        raise ValueError("Missing identifier type")
    if identifier_type.lower() not in ["primary", "secondary", "psimi"]:
        raise ValueError("Identifier type must be of type PRIMARY, SECONDARY OR PSIMI")
    return identifier_type.upper()


def create_merchant_identifier_fields(
    payment_provider_slug,
    identifier,
    identifier_type,
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
        identifier=identifier,
        identifier_type=identifier_type,
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


def insert_mids(mids_data: list[dict], session: db.Session) -> int:
    def do_insert():
        db.engine.execute(insert(models.MerchantIdentifier.__table__).values(mids_data).on_conflict_do_nothing())
        session.commit()

    mids_table_before = db.run_query(
        session.query(models.MerchantIdentifier).count,
        session=session,
        read_only=True,
        description="count MIDs before import",
    )
    db.run_query(do_insert, session=session, description="onboard MIDs")
    mids_table_after = db.run_query(
        session.query(models.MerchantIdentifier).count,
        session=session,
        read_only=True,
        description="count MIDs after import",
    )

    return mids_table_after - mids_table_before


def add_identifiers_from_csv(
    file_storage: werkzeug.datastructures.FileStorage, *, session: db.Session
) -> tuple[int, int]:
    mark = _get_first_character(file_storage)
    if mark not in string.printable:
        raise ValueError(
            "File starts with an invalid character. Ensure the file has been saved in UTF-8 format with no BOM."
        )

    reader = csv.reader((line.decode() for line in file_storage), dialect=CSVDialect())

    log.debug("Processing MIDs...")

    mids_fields: list[dict] = []
    for line, row in enumerate(reader):
        row = [value.strip() for value in row]
        try:
            (
                payment_provider_slug,
                identifier,
                identifier_type,
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

        identifier_type = validate_identifier_type(identifier_type)

        mid_fields = create_merchant_identifier_fields(
            payment_provider_slug,
            identifier,
            identifier_type,
            location_id,
            merchant_internal_id,
            loyalty_scheme_slug,
            location,
            postcode,
            session=session,
        )
        mids_fields.append(mid_fields)

    n_mids_in_file = len(mids_fields)
    log.debug(f'Importing {n_mids_in_file} MIDs from "{file_storage.name}"')

    count = insert_mids(mids_fields, session=session)

    return n_mids_in_file, count


@api.route("/csv", methods=["POST"])
@requires_auth(auth_scopes="mids:write")
@view_session
def import_identifiers(*, session: db.Session) -> tuple[dict, int]:
    """
    Import identifiers
    ---
    post:
        description: Upload identifiers CSV file
        responses:
            200:
                description: "Import was successful"
    """
    imported: t.List[dict] = []
    failed: t.List[dict] = []

    def fail(filepath: str, reason: str) -> None:
        failed.append({"file": filepath, "reason": reason})

    for filepath, file_storage in request.files.items():
        log.debug(f'Attempting to import identifiers file "{filepath}"')
        if file_storage.content_type != "text/csv":
            fail(filepath, f"Expected file content type text/csv, got {file_storage.content_type}")
            continue
        try:
            n_mids_in_file, n_mids_imported = add_identifiers_from_csv(file_storage, session=session)
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


@api.route("/", methods=["POST"])
@requires_service_auth
def onboard_identifiers() -> tuple[dict, int]:
    """
    Onboard identifiers
    ---
    post:
        description: Onboard a number of MIDs, Secondary MIDs, or PSIMIs.
        parameters:
        - in: body
          schema: MIDCreationListSchema
        responses:
            200:
                description: "The identifiers were onboarded successfully"
                schema: MIDCreationResultSchema
            400:
                description: "Bad request content type"
            422:
                description: "Invalid request schema"
    """
    if not request.is_json:
        return {"title": "Bad request", "description": "Expected JSON content type"}, 400

    request_schema = schemas.MIDCreationListSchema()

    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return {"title": "Validation error", "description": ex.messages}, 422

    with db.session_scope() as session:
        identifiers = [
            create_merchant_identifier_fields(
                identifier=identifier["identifier"],
                identifier_type=validate_identifier_type(identifier.get("identifier_type")),
                location_id=identifier.get("location_id"),
                merchant_internal_id=identifier.get("merchant_internal_id"),
                loyalty_scheme_slug=identifier["loyalty_plan"],
                payment_provider_slug=identifier["payment_scheme"],
                location="",
                postcode="",
                session=session,
            )
            for identifier in data["identifiers"]
        ]

        count = insert_mids(identifiers, session=session)

    return {"total": len(identifiers), "onboarded": count}, 200


@api.route("/deletion", methods=["POST"])
@requires_service_auth
def offboard_mids() -> tuple[dict, int]:
    """
    Offboard identifiers
    ---
    post:
        description: Offboard a number of MIDs, Secondary MIDs, or PSIMIs.
        parameters:
        - in: body
          schema: MIDDeletionListSchema
        responses:
            200:
                description: "The identifiers were offboarded successfully"
                schema: MIDDeletionResultSchema
            400:
                description: "Bad request content type"
            422:
                description: "Invalid request schema"
    """
    if not request.is_json:
        return {"title": "Bad request", "description": "Expected JSON content type"}, 400

    request_schema = schemas.MIDDeletionListSchema()
    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return {"title": "Validation error", "description": ex.messages}, 422

    with db.session_scope() as session:
        q = (
            session.query(models.MerchantIdentifier.id)
            .join(models.PaymentProvider)
            .filter(
                tuple_(models.MerchantIdentifier.identifier, models.PaymentProvider.slug).in_(
                    [(mid["mid"], mid["payment_scheme"]) for mid in data["mids"]]
                )
                | models.MerchantIdentifier.location_id.in_(data["locations"])
            )
        )
        mid_ids = db.run_query(
            q.all,
            session=session,
            description="find MID IDs for offboarding by (mid, payment_slug) or location",
        )

        count = db.run_query(
            session.query(models.MerchantIdentifier)
            .filter(models.MerchantIdentifier.id.in_([r.id for r in mid_ids]))
            .delete,
            session=session,
            description="delete MIDs by ID",
        )

    return {"deleted": count}, 200
