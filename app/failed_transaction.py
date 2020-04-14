import hashlib

from app import db


class FailedTransaction:
    class NoSuchTransaction(Exception):
        pass

    def __init__(self, max_retries: int = 3) -> None:
        """
        Create a failed matched transaction store.
        """
        self.max_retries = max_retries

    @staticmethod
    def _key(scheme_slug: str, transaction_id: int) -> str:
        """
        Creates a key for the given transaction.
        :param scheme_slug: The slug belonging to the agent.
        :param transaction_id: Merchant (third party) transaction id
        :return: A string key to use as the key for the failed transaction.
        """
        key = f"{scheme_slug}.{transaction_id}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return f"transaction:{key_hash}"

    def retry(self, scheme_slug: str, transaction_id: int) -> bool:
        """
        Checks how many retries a transaction has had. If no transaction is found it will create a new one and set a
        time limit of 5 days on the key. Each time a transaction fails it will be queried here and it's count will
        increment by one until it reaches it's retry limit. If a transaction is successful it wont be queried again but
        will expire after 5 days anyway.
        :param scheme_slug: Used to create the first part of the hash used for the key
        :param transaction_id: Used to create the second part of the hash used for the key
        :return: True if retry limit has been reached, otherwise false.
        """
        key = self._key(scheme_slug, transaction_id)
        limit_reached = False
        retries_value = db.redis.get(key)
        if retries_value:
            retries = int(retries_value)
            if retries <= self.max_retries:
                db.redis.incr(key)
            else:
                db.redis.delete(key)
                limit_reached = True
        else:
            # 432000 seconds == 5 days
            db.redis.set(key, 0, ex=432000, nx=True)
        return limit_reached
