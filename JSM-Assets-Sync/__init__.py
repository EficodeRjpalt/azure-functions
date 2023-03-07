import logging
import requests
import asyncio
from pprint import pprint
from os import getenv
import dotenv

import azure.functions as func

def get_organization_user_info():

    user_attribute_ids = ['983', '980']

    assets_workspace = getenv('workspace_id')
    org_endpoint = f'https://api.atlassian.com/jsm/assets/workspace/{assets_workspace}/v1/aql/objects?qlQuery=objectType=Organizations'
    results = requests.get(
        org_endpoint,
        auth=(
            getenv('EMAIL'),
            getenv('API_TOKEN')
        )
    )

    object_entries = results.json()['objectEntries']

    org_users_info = []

    for entry in object_entries:
        self_url = entry['_links']['self']
        for attribute in entry['attributes']:
            if attribute['objectTypeAttributeId'] in user_attribute_ids:
                pprint(attribute)



def main(req: func.HttpRequest) -> func.HttpResponse:

    dotenv.load_dotenv()
    logging.info('Python HTTP trigger function processed a request.')
    
    get_organization_user_info()

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
