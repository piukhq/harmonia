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
from app.identifiers import schemas

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


def insert_identifiers(identifiers_data: list[dict], session: db.Session) -> int:
    def do_insert():
        db.engine.execute(insert(models.MerchantIdentifier.__table__).values(identifiers_data).on_conflict_do_nothing())
        session.commit()

    identifiers_table_before = db.run_query(
        session.query(models.MerchantIdentifier).count,
        session=session,
        read_only=True,
        description="count identifiers before import",
    )
    db.run_query(do_insert, session=session, description="onboard identifiers")
    identifiers_table_after = db.run_query(
        session.query(models.MerchantIdentifier).count,
        session=session,
        read_only=True,
        description="count identifiers after import",
    )

    return identifiers_table_after - identifiers_table_before


def add_identifiers_from_csv(
    file_storage: werkzeug.datastructures.FileStorage, *, session: db.Session
) -> tuple[int, int]:
    mark = _get_first_character(file_storage)
    if mark not in string.printable:
        raise ValueError(
            "File starts with an invalid character. Ensure the file has been saved in UTF-8 format with no BOM."
        )

    reader = csv.reader((line.decode() for line in file_storage), dialect=CSVDialect())

    log.debug("Processing identifiers...")

    identifiers_fields: list[dict] = []
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

        identifier_fields = create_merchant_identifier_fields(
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
        identifiers_fields.append(identifier_fields)

    n_identifiers_in_file = len(identifiers_fields)
    log.debug(f'Importing {n_identifiers_in_file} identifiers from "{file_storage.name}"')

    count = insert_identifiers(identifiers_fields, session=session)

    return n_identifiers_in_file, count


@api.route("/csv", methods=["POST"])
@requires_auth(auth_scopes="identifiers:write")
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
            n_identifiers_in_file, n_identifiers_imported = add_identifiers_from_csv(file_storage, session=session)
        except Exception as ex:
            error_message = f"{type(ex).__name__}: {ex}"
            if len(error_message) > 250:
                error_message = f"{error_message[:248]} …"
            fail(filepath, error_message)
        else:
            imported.append({"file": filepath, "in_file": n_identifiers_in_file, "imported": n_identifiers_imported})

    # clear the caches to avoid getting cached objects from old sessions
    get_loyalty_scheme.cache_clear()
    get_payment_provider.cache_clear()

    return {"imported": imported, "failed": failed}, 200


@api.route("", methods=["POST"])
@requires_service_auth
def onboard_identifiers() -> tuple[dict, int]:
    """
    Onboard identifiers
    ---
    post:
        description: Onboard a number of Primary identifiers, Secondary identifiers, or PSIMIs.
        parameters:
        - in: body
          schema: IdentifierCreationListSchema
        responses:
            200:
                description: "The identifiers were onboarded successfully"
                schema: IdentifierCreationResultSchema
            400:
                description: "Bad request content type"
            422:
                description: "Invalid request schema"
    """
    if not request.is_json:
        return {"title": "Bad request", "description": "Expected JSON content type"}, 400

    request_schema = schemas.IdentifierCreationListSchema()

    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return {"title": "Validation error", "description": ex.messages}, 422

    with db.session_scope() as session:
        identifiers = [
            create_merchant_identifier_fields(
                identifier=identifier["identifier"],
                identifier_type=identifier.get("identifier_type"),
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

        count = insert_identifiers(identifiers, session=session)

    return {"total": len(identifiers), "onboarded": count}, 200


@api.route("/deletion", methods=["POST"])
@requires_service_auth
def offboard_identifiers() -> tuple[dict, int]:
    """
    Offboard identifiers
    ---
    post:
        description: Offboard a number of Primary identifiers, Secondary identifiers, or PSIMIs.
        parameters:
        - in: body
          schema: IdentifierDeletionListSchema
        responses:
            200:
                description: "The identifiers were offboarded successfully"
                schema: IdentifierDeletionResultSchema
            400:
                description: "Bad request content type"
            422:
                description: "Invalid request schema"
    """
    if not request.is_json:
        return {"title": "Bad request", "description": "Expected JSON content type"}, 400

    request_schema = schemas.IdentifierDeletionListSchema()
    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return {"title": "Validation error", "description": ex.messages}, 422

    with db.session_scope() as session:
        q = (
            session.query(models.MerchantIdentifier.id)
            .join(models.PaymentProvider)
            .filter(
                tuple_(
                    models.MerchantIdentifier.identifier,
                    models.MerchantIdentifier.identifier_type,
                    models.PaymentProvider.slug,
                ).in_(
                    [
                        (identifier["identifier"], identifier["identifier_type"], identifier["payment_scheme"])
                        for identifier in data["identifiers"]
                    ]
                )
                | models.MerchantIdentifier.location_id.in_(data["locations"])
            )
        )
        identifier_ids = db.run_query(
            q.all,
            session=session,
            description="find identifiers for offboarding by (identifier, payment_slug) or location",
        )

        count = db.run_query(
            session.query(models.MerchantIdentifier)
            .filter(models.MerchantIdentifier.id.in_([r.id for r in identifier_ids]))
            .delete,
            session=session,
            description="delete identifiers by ID",
        )

    return {"deleted": count}, 200


@api.route("/<payment_provider>/<identifier_type>/<identifier>", methods=["PATCH"])
@requires_service_auth
def update_identifiers(payment_provider: str, identifier_type: str, identifier: str) -> tuple[dict, int]:
    """
    Update identifier
    ---
    patch:
        description: update a single Primary identifier, Secondary identifier, or PSIMI.
        parameters:
        - in: body
          schema: IdentifierUpdateSchema
        responses:
            200:
                description: "The identifier was updated successfully"
                schema: IdentifierUpdateSchema
            400:
                description: "Bad request content type"
            422:
                description: "Invalid request schema"
    """

    if not request.is_json:
        return {"title": "Bad request", "description": "Expected JSON content type"}, 400

    request_schema = schemas.IdentifierUpdateSchema()

    try:
        data = request_schema.load(request.json)
    except marshmallow.ValidationError as ex:
        return {"title": "Validation error", "description": ex.messages}, 422

    with db.session_scope() as session:
        q = (
            session.query(models.MerchantIdentifier)
            .join(models.PaymentProvider)
            .filter(
                models.PaymentProvider.slug == payment_provider,
                models.MerchantIdentifier.identifier == identifier,
                models.MerchantIdentifier.identifier_type == identifier_type.upper(),
            )
            .one_or_none()
        )

        if q is None:
            return {"title": "MID not in Harmonia", "description": "MID is not present within Harmonia"}, 404

        if location_id := data.get("location_id"):
            q.location_id = location_id

        if merchant_internal_id := data.get("merchant_internal_id"):
            q.merchant_internal_id = merchant_internal_id

        session.commit()

    return {}, 200
