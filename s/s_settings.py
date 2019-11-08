from settings import getenv


# Environment variables used for local testing:

# Cooperative flag to run end to end test with s/test
ICELAND_END_TO_END_TEST = getenv("TXM_ICELAND_END_TO_END_TEST", "")

# Path for file with transactions for Iceland
ICELAND_FILE_WITH_TRANSACTIONS_PATH = getenv("TXM_ICELAND_FILE_WITH_TRANSACTIONS_PATH", "")

# Limit of transactions from file that will be produced for Iceland
ICELAND_LIMIT_TRANSACTIONS_FROM_FILE = getenv("TXM_ICELAND_LIMIT_TRANSACTIONS_FROM_FILE", "10")
