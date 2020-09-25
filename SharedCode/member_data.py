import logging
import os
import stripe
stripe.api_key = os.environ["STRIPE_SECRET"]
from datetime import datetime

class MemberData:
    def __init__(self, name, email, company, country, start, end, type, recurring):
        self.name = name
        self.email = email
        self.company = company
        self.country = country
        self.start = datetime.strptime(start, "%Y-%m-%d")
        self.end = datetime.strptime(end, "%Y-%m-%d")
        self.type = type
        self.recurring = recurring
   
    def UpdateMetadata(self, customer_id, metadata):
        stripe.Customer.modify(
                            customer_id,
                            metadata=metadata
                        )
    def CreateCustomer(self):
        stripe.Customer.create(email=self.email.lower(), 
                                       name=self.name,
                                       metadata = {
                                           'membership_type':self.type,
                                           'membership_start':datetime.strftime(self.start, '%Y-%m-%d'),
                                           'membership_end':datetime.strftime(self.end, '%Y-%m-%d'),
                                           'membership_recurring':self.recurring,
                                           'company':self.company,
                                           'country':self.country
                                       })