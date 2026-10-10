import os

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableClient


def get_email_notify_table_client() -> TableClient:
    account_name = os.environ["STORAGE_ACCOUNT"]
    account_key = os.environ["STORAGE_KEY"]
    table_name = os.environ["EMAIL_NOTIFY_TABLE"]
    endpoint = f"https://{account_name}.table.core.windows.net"

    return TableClient(
        endpoint=endpoint,
        table_name=table_name,
        credential=AzureNamedKeyCredential(account_name, account_key),
    )
