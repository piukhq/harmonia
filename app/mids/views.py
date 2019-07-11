import csv
import typing as t

from flask import Blueprint, request, jsonify
import werkzeug

from app import models, db
import settings


api = Blueprint("mids_api", __name__, url_prefix=f"{settings.URL_PREFIX}/mids")


ResponseType = t.Tuple[t.Dict, int]


class CSVDialect(csv.Dialect):
    delimiter = ","
    escapechar = '"'
    lineterminator = "\n"
    quoting = csv.QUOTE_NONE


def create_mid_from_item(item: dict) -> dict:
    loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug=item["loyalty_scheme_slug"])
    payment_provider, _ = db.get_or_create(models.PaymentProvider, slug=item["payment_provider_slug"])

    return dict(
        mid=item["mid"],
        loyalty_scheme_id=loyalty_scheme.id,
        payment_provider_id=payment_provider.id,
        location=item["location"],
        postcode=item["postcode"],
    )


def add_mids_from_csv(file_storage: werkzeug.datastructures.FileStorage) -> None:
    reader = csv.DictReader(
        (line.decode() for line in file_storage),
        fieldnames=(
            "payment_provider_slug",
            "mid",
            "loyalty_scheme_slug",
            "loyalty_scheme_name",
            "location",
            "postcode",
            "action",
        ),
        dialect=CSVDialect(),
    )

    mids = [create_mid_from_item(item) for item in reader if not (item["action"] and item["action"].lower() != "a")]

    def insert_mids():
        db.engine.execute(models.MerchantIdentifier.__table__.insert().values(mids))
        db.session.commit()

    db.run_query(insert_mids)


@api.route("/", methods=["POST"])
def import_mids() -> ResponseType:
    """Import MIDs"""
    imported: t.List[str] = []
    failed: t.List[t.Dict[str, str]] = []

    def fail(filepath: str, reason: str) -> None:
        failed.append({"file": filepath, "reason": reason})

    for filepath, file_storage in request.files.items():
        if file_storage.content_type != "text/csv":
            fail(filepath, "Content type must be text/csv")
            continue
        try:
            add_mids_from_csv(file_storage)
        except Exception as ex:
            error_message = str(ex)
            if len(error_message) > 250:
                error_message = f"{error_message[:248]} …"
            fail(filepath, error_message)
        else:
            imported.append(filepath)

    return jsonify({"imported": imported, "failed": failed}), 200
