import os
import json
import logging
import stripe
import azure.functions as func
from ..SharedCode.eventbot import registrant


def main(msg: func.QueueMessage) -> None:
    payload = json.loads(msg.get_body().decode('utf-8'))

    job_type = payload.get('job_type', None)
    job_payload =  payload.get('payload', {})

    if job_type == 'order.created':
        handle_order_created(job_payload.get('id'))
    elif job_type == 'charge.refunded':
        handle_order_refunded(job_payload.get('id'), job_payload.get('amount_refunded'))


def update_product_inventory(order):
    for item in order.get('items', []):
        if item['type'] != 'sku':
            continue

        sku = stripe.SKU.retrieve(item['parent'], api_key=os.environ['STRIPE_SECRET'])
        inventory = sku['metadata'].get('inventory', None)

        if inventory is None or int(inventory) == 0:
            continue

        inventory = int(inventory) - 1
        stripe.SKU.modify(sku['id'], metadata={'inventory': inventory}, api_key=os.environ['STRIPE_SECRET'])


def update_discount_code_inventory(order):
    discount_code = order.get('metadata', {}).get('discount_code', None)

    if discount_code is not None:
        discount_code = discount_code.strip().upper()
        coupon = stripe.Coupon.retrieve(discount_code, api_key=os.environ['STRIPE_SECRET'])
        inventory = coupon['metadata'].get('inventory', None)

        if inventory is not None and int(inventory) != 0:
            inventory = int(inventory) - 1
            stripe.Coupon.modify(discount_code, metadata={'inventory': inventory}, api_key=os.environ['STRIPE_SECRET'])


def handle_order_created(order_id):
    order = stripe.Order.retrieve(order_id, api_key=os.environ['STRIPE_SECRET'])

    update_product_inventory(order)
    update_discount_code_inventory(order)
    registrant.add_order(order)


def handle_order_refunded(charge_id, amount_refunded):
    registrant.add_refund(charge_id, amount_refunded)
