import os
import azure.functions as func
import datetime
import logging
import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]


def main(mytimer: func.TimerRequest) -> None:
    try:
        utc_timestamp = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc).isoformat()

        logging.info('Python timer trigger function ran at %s', utc_timestamp)
        
        #check for the last customer processed, if any, and continue from there
        try:
            last_processed_file = open('stripe-customer-cleanup-last-processed.txt', 'r') 
            line = last_processed_file.readline() 
            if not line == '':
                last_customer_id = line
                logging.info("starting from last customer processed: " + last_customer_id)
            else:
                last_customer_id = None
        except:
            logging.exception("Error opening file stripe-customer-cleanup-last-processed.txt:")
            last_customer_id = None
        
        customers = stripe.Customer.list(limit=100, starting_after=last_customer_id)
        for customer in customers.auto_paging_iter():
            removed = RemoveInvalidCustomer(customer)
            if not removed:
                FixEmailCasing(customer)
            with open('stripe-customer-cleanup-last-processed.txt', 'w') as processed_file:
                processed_file.write(customer['id'])
            logging.info("done processing customer: " + customer['id'])
        
        logging.info("finished processing all customers.  Cleaning up last processed file.")
        with open('stripe-customer-cleanup-last-processed.txt', 'w') as processed_file:
                processed_file.write('') 

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        raise


def RemoveInvalidCustomer(customer):
    try:
        customer_id = customer['id']

        # check for metadata
        metadata = customer['metadata']
        if metadata != {}:
            logging.info("keep " + customer_id +
                        " since metadata is not empty")
            return False

        # check for active subscriptions
        active_subscription_count = customer["subscriptions"]["total_count"]
        if active_subscription_count > 0:
            logging.info(
                "keep " + customer_id + " since active subscription count is " + str(active_subscription_count))
            return False

        # check for any subscriptions
        any_subscription_count = len(
            stripe.Subscription.list(customer=customer_id, status="all", limit=1))
        if any_subscription_count > 0:
            logging.info(
                "keep " + customer_id + " since any subscription count is " + str(any_subscription_count))
            return False

        # check if they have any invoices
        invoice_count = len(stripe.Invoice.list(
            customer=customer_id, limit=1))
        if invoice_count > 0:
            logging.info("keep " + customer_id +
                        " since invoice count is > 0")
            return False

        # check if they have any orders
        order_count = len(stripe.Order.list(customer=customer_id, limit=1))
        if order_count > 0:
            logging.info("keep " + customer_id +
                        " since order count is > 0")
            return False

        # check for any payments not canceled or blocked
        payments = stripe.PaymentIntent.list(
            customer=customer_id, limit=100)
        valid_payment_found = False
        for payment_intent in payments.auto_paging_iter():
            if payment_intent["status"] != "canceled":
                # look for a blocked charge
                if len(payment_intent["charges"]["data"]) > 0 and payment_intent["charges"]["data"][0]["outcome"]["type"] == 'blocked':
                    break
                valid_payment_found = True
                logging.info("keep " + customer_id +
                            " since a valid payment found")
                break

        if valid_payment_found:
            return False

        # didn't meet any of the criterias
        stripe.Customer.modify(customer_id, metadata={
            "cleanup_customer": "true"},)
        stripe.Customer.modify(customer_id, metadata={
            "cleanup_date": datetime.datetime.today().strftime('%Y-%m-%d')},)
        logging.info("delete " + customer_id)
        return True

    except APIConnectionError as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        return False

    except Exception as ex:
        template = "An exception of type {0} occurred while processing a customer. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.exception(message)
        return False

    


def FixEmailCasing(customer):
    email = customer["email"]
    customer_id = customer['id']

    if (any(char.isupper() for char in email)):
        stripe.Customer.modify(customer_id, metadata={
            "cleanup_case": "true"},)
        stripe.Customer.modify(customer_id, metadata={
            "cleanup_date": datetime.datetime.today().strftime('%Y-%m-%d')},)
        logging.info("cleanup " + customer_id + " with email " + email)
    else:
        logging.info("already lowercase " +
                     customer_id + " with email " + email)

    return
