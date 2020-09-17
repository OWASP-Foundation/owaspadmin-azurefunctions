import os
import hashlib
from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError
from datetime import datetime
import stripe


class OWASPMailchimp:
    mailchimp = MailChimp(mc_api=os.environ["MAILCHIMP_API_KEY"])
    
    def GetMailchimpSubscriberHash(self, email):
        email = email.lower()
        hashed = hashlib.md5(email.encode('utf8'))

        return hashed.hexdigest()

    def AddToMailingList(self, email, metadata, subscription_data, customer_id):
        subscriber_hash = self.GetMailchimpSubscriberHash(email)
        request_data = {
            "email_address": email,
            "status_if_new": "subscribed",
            "status": "subscribed",
            "merge_fields": self.GetMergeFields(metadata, subscription_data, customer_id),
            "interests": self.GetInterests(metadata),
            "marketing_permissions": self.GetMarketingPermissions(metadata)
        }

        list_member = self.mailchimp.lists.members.create_or_update(os.environ["MAILCHIMP_LIST_ID"], subscriber_hash, request_data)

        return list_member   

    def GetMarketingPermissions(self, metadata):
        if metadata.get('mailing_list', 'False') == 'True':
            return [
                {
                    "marketing_permission_id": os.environ["MAILCHIMP_MKTG_PERMISSIONS_ID"],
                    "enabled": True
                }
            ]
        else:
            return [
                {
                    "marketing_permission_id": os.environ["MAILCHIMP_MKTG_PERMISSIONS_ID"],
                    "enabled": False
                }
            ]

    def GetInterests(self, metadata):
        purchase_type = metadata.get('purchase_type')

        if purchase_type == 'donation':
            return {
                os.environ["MAILCHIMP_DONOR_GROUP_ID"]: True
            }
        else:
            return {
                os.environ["MAILCHIMP_MEMBER_GROUP_ID"]: True
            }

    def GetMergeFields(self, metadata, subscription_data, customer_id):
        merge_fields = {}

        purchase_type = metadata.get('purchase_type', 'donation')
        name = metadata.get('name')
        source = metadata.get('source')

        merge_fields['NAME'] = name

        if source is not None:
            merge_fields['SOURCE'] = source

        if purchase_type == 'membership':
            company = metadata.get('company')
            country = metadata.get('country')
            postal_code = metadata.get('postal_code')

            merge_fields['MEMSTART'] = datetime.today().strftime('%m/%d/%Y')

            customer = stripe.Customer.retrieve(
                customer_id,
                api_key=os.environ["STRIPE_SECRET"]
            )
            customer_metadata = customer.get('metadata', {})

            membership_start = customer_metadata.get('membership_start', '')
            membership_end = customer_metadata.get('membership_end', '') #should this return 'NULL' string and then compare via None as below?  Changed to ''
            membership_type = customer_metadata.get('membership_type', '')
            membership_recurring = customer_metadata.get('membership_recurring', 'no')

            if membership_start is not None:
                merge_fields['MEMSTART'] = membership_start
            if membership_end is not None:
                merge_fields['MEMEND'] = membership_end
            if membership_type is not None:
                merge_fields['MEMTYPE'] = membership_type
            if membership_recurring is not None:
                merge_fields['MEMRECUR'] = membership_recurring
            if company is not None:
                merge_fields['COMPANY'] = company
            if country is not None:
                merge_fields['COUNTRY'] = country
            if postal_code is not None:
                merge_fields['POSTALCODE'] = postal_code

        return merge_fields