import hashlib

from redis import StrictRedis


class FailedTransaction:
    class NoSuchTransaction(Exception):
        pass

    def __init__(self, redis_url: str, max_retries: int = 3) -> None:
        """
        Create a failed matched transaction store.
        """
        self.max_retries = max_retries
        self.storage = StrictRedis.from_url(redis_url)

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
        return "transaction:{}".format(key_hash)

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
        retries = self.storage.get(key)
        if retries:
            retries = int(retries.decode("utf-8"))
            if retries <= self.max_retries:
                self.storage.incr(key)
            else:
                self.storage.delete(key)
                limit_reached = True
        else:
            # 432000 seconds == 5 days
            self.storage.set(key, 0, ex=432000, nx=True)
        return limit_reached
