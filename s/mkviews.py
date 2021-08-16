#! /usr/bin/env python3
from app.db import session

merchants_query = """
SELECT
    mi.mid,
    mi.location,
    mi.postcode,
    pp.slug AS payment_provider_slug,
    ls.slug AS loyalty_scheme_slug
FROM merchant_identifier as mi
    INNER JOIN payment_provider pp ON pp.id = mi.payment_provider_id
    INNER JOIN loyalty_scheme ls ON ls.id = mi.loyalty_scheme_id;
"""


if __name__ == "__main__":
    session.execute(f"CREATE OR REPLACE VIEW merchants_view AS {merchants_query}")
    session.commit()
