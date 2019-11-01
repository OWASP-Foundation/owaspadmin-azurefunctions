import logging

import azure.functions as func

FIRST_NAME_FIELD = 'Field148'
LAST_NAME_FIELD = 'Field149'
EMAIL_FIELD = 'Field10'
MEMBERSHIP_TYPE_FIELD = 'Field260'
COUNTRY_FIELD = 'Field13'
POSTAL_CODE_FIELD = 'Field11'
UNIVERSITY_FIELD = 'Field262'
GRADUATION_DATE_FIELD = 'Field264'
FAVORITE_CLASS_FIELD = 'Field265'
DATE_CREATED_FIELD = 'DateCreated'

#8bdef88baad8843

def main(req: func.HttpRequest) -> func.HttpResponse:
    return HttpResponse('Nothing to see here' status_code=400)
    logging.info('Student Membership webhook called')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello {name}!")
    else:
        return func.HttpResponse(
             "Please pass a name on the query string or in the request body",
             status_code=400
        )
