import os
import json
import stripe
import gspread
import logging
from datetime import datetime
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


def get_spreadsheet_name(event):
    event_name = event.get('name', '')
    event_date = event['metadata'].get('event_date', None)

    if event_date is None:
        event_year = datetime.now().year
    else:
        event_year = datetime.strptime(event_date, '%Y-%m-%d').year

    return str(event_year) + ' ' + str(event_name)


def create_spreadsheet(event):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(client_secret, scope)
    drive = build('drive', 'v3', credentials=creds, cache_discovery=False)
    sheet_name = get_spreadsheet_name(event)

    file_metadata = {
        'name': sheet_name,
        'parents': [os.environ['EVENT_REGISTRATION_FOLDER']],
        'mimeType': 'application/vnd.google-apps.spreadsheet',
    }

    drive.files().create(body=file_metadata, supportsAllDrives=True).execute()

    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1

    row_headers = ['Customer ID', 'First Name', 'Last Name', 'Company/Organization', 'Title', 'Email', 'Discount Code', 'Country', 'City', 'Gluten-Free', 'Halal', 'Kosher', 'Nut Allergy', 'Shellfish Allergy', 'Vegan', 'Vegetarian', 'Experience', 'Persona', 'Payment Date', 'Payment Amount', 'Refund Amount', 'Payment ID', 'Order ID', 'Payment Fees', 'SKU', 'Session']

    sheet.append_row(row_headers)


def add_order(order):
    event = stripe.Product.retrieve(order['metadata'].get('event_id'), api_key=os.environ['STRIPE_SECRET'])

    sheet = get_google_sheet(get_spreadsheet_name(event))
    row_data = get_base_row_data_for_order(order)

    for item in order['items']:
        if item['type'] != 'sku':
            continue

        sku = stripe.SKU.retrieve(item['parent'], api_key=os.environ['STRIPE_SECRET'])
        sku_row = row_data.copy()
        sku_row.extend([sku['id'], sku['attributes'].get('name', '')])

        sheet.append_row(sku_row)


def add_refund(charge_id, amount_refunded):
    charge = stripe.Charge.retrieve(charge_id, api_key=os.environ['STRIPE_SECRET'])
    event_id = charge['metadata'].get('event_id', None)

    if event_id is None:
        return

    event = stripe.Product.retrieve(charge['metadata'].get('event_id'), api_key=os.environ['STRIPE_SECRET'])

    sheet = get_google_sheet(get_spreadsheet_name(event))
    cell_list = sheet.findall(charge_id)

    for cell in cell_list:
        sheet.update_cell(cell.row, 21, amount_refunded / 100)


def get_google_sheet(sheet_name):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    client_secret = json.loads(os.environ['GOOGLE_CREDENTIALS'], strict=False)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(client_secret, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1

    return sheet


def get_base_row_data_for_order(order):
    dietary_restrictions = order['metadata'].get('dietary_restrictions', '').strip().split('|')
    charge_id = order['metadata'].get('charge_id', None)

    if charge_id is not None:
        charge = stripe.Charge.retrieve(charge_id, api_key=os.environ['STRIPE_SECRET'])
        balance_transaction = stripe.BalanceTransaction.retrieve(charge['balance_transaction'], api_key=os.environ['STRIPE_SECRET'])
        payment_fee = balance_transaction['fee'] / 100
    else:
        payment_fee = ''

    row_data = [
        order['customer'],
        order['metadata'].get('name', '').strip().split(' ')[0],
        ' '.join((order['metadata'].get('name', '') + ' ').split(' ')[1:]).strip(),
        order['metadata'].get('company', ''),
        order['metadata'].get('title', ''),
        order['email'],
        order['metadata'].get('discount_code', ''),
        order['metadata'].get('country', ''),
        order['metadata'].get('city', ''),
        'YES' if 'Gluten-Free' in dietary_restrictions else '',
        'YES' if 'Halal' in dietary_restrictions else '',
        'YES' if 'Kosher' in dietary_restrictions else '',
        'YES' if 'Nut Allergy' in dietary_restrictions else '',
        'YES' if 'Shellfish Allergy' in dietary_restrictions else '',
        'YES' if 'Vegan' in dietary_restrictions else '',
        'YES' if 'Vegetarian' in dietary_restrictions else '',
        order['metadata'].get('experience', ''),
        order['metadata'].get('persona', ''),
        datetime.fromtimestamp(order['created']).strftime("%m/%d/%Y"),
        order['amount'] / 100,
        '',
        order['metadata'].get('charge_id', ''),
        order['id'],
        payment_fee
    ]

    return row_data
