import logging

import azure.functions as func
from ..SharedCode.copper import OWASPCopper

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('RunCurrentTests started.')

    # This function will be modified to run various functional testing on proposed changes with the API
    # Currently testing proposed changes to the membership to include address requirements
    try:
        address = req.get_json()
    except ValueError:
        pass
    email = 'harold.blankenship@owasp.com'

    logging.info("Updating %s address.", email)
    cp = OWASPCopper()
    person = cp.FindPersonByEmailObj(email)[0]
    current_address = person['address']
    
    cp_address = {
                "street": address["line1"] + " " + address["line2"],
                "city": address["city"],
                "state": address["state"],
                "postal_code": address["postal_code"]
            }
    logging.info(f"changing from {current_address} to {cp_address}")
    cp.UpdatePersonAddress(person['id'], cp_address)
    #refresh person
    person = cp.FindPersonByEmailObj(email)[0]
    logging.info(f"Address updated result: {validate_address(person['address'], cp_address)}")

    logging.info("RunCurrentTests finished.")
    return func.HttpResponse(
            "This HTTP triggered function executed successfully.",
            status_code=200
    )

def validate_address(address1, address2):
    return address1['street'] == address2['street'] and address1['city'] == address2['city'] and address1['state'] == address2['state'] and address1['postal_code'] == address2['postal_code']