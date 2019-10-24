from settings import getenv


# Environment variables used for local testing:

# Cooperative flag to run end to end test with s/test
COOP_END_TO_END_TEST = getenv("TXM_COOPERATIVE_END_TO_END_TEST", "")

# Path for file with transactions for Cooperative
COOP_FILE_WITH_TRANSACTIONS_PATH = getenv("TXM_COOP_FILE_WITH_TRANSACTIONS_PATH", "")

# Limit of transactions from file that will be produced for Cooperative
COOP_LIMIT_TRANSACTIONS_FROM_FILE = getenv("TXM_COOP_LIMIT_TRANSACTIONS_FROM_FILE", "10")
