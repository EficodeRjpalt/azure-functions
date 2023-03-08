import logging
from pprint import pprint
import asyncio
from os import getenv
import requests
import dotenv

import azure.functions as func

def get_all_org_object_keys() -> list:

    assets_workspace = getenv('workspace_id')
    org_endpoint = f'https://api.atlassian.com/jsm/assets/workspace/{assets_workspace}/v1/aql/objects?qlQuery=objectType=Organizations'
    results = requests.get(
        org_endpoint,
        auth=(
            getenv('EMAIL'),
            getenv('API_TOKEN')
        ),
        timeout=30
    )

    object_entries = results.json()['objectEntries']

    return [str(ass_object['id']) for ass_object in object_entries]


def get_all_objects(object_ids: list) -> None:

    query_string = ','.join(object_ids)

    aql_query = f'https://api.atlassian.com/jsm/assets/workspace/b7643ce5-0549-46b0-bafe-366a0939e44d/v1/aql/objects?qlQuery=objectId%20in%20({query_string})'

    results = requests.get(
        aql_query,
        auth=(
            getenv('EMAIL'),
            getenv('API_TOKEN')
        ),
        timeout=30
    )

    # Not quite robust patch here. Will the attribute type ID always be the same?
    attribute_ids = get_attribute_ids(getenv('MEMBER_ATTR_NAME'), results.json())
    attribute_id = -1

    if len(attribute_ids) == 1:
        attribute_id = list(attribute_ids.values())[0]
    else:
        logging.info('Multiple Customer fields present. Do something.')
        

    for entry in results.json()['objectEntries']:
        entry_attr_ids = [attribute['objectTypeAttributeId'] for attribute in entry['attributes']]
        pprint(entry_attr_ids)
        if attribute_id in entry_attr_ids:
            assets_object = build_assets_object(entry)


def get_attribute_ids(attribute_name: str, response_body: dict) -> dict:

    attribute_id_dict = {attribute_info['name']: attribute_info['id'] for attribute_info in response_body['objectTypeAttributes'] if attribute_info['name'] == attribute_name}

    return attribute_id_dict

def build_assets_object(object_entry: dict) -> dict:

    org_name = entry[]

def main(req: func.HttpRequest) -> func.HttpResponse:

    dotenv.load_dotenv()
    logging.info('Python HTTP trigger function processed a request.')
    
    object_keys = get_all_org_object_keys()
    get_all_objects(object_keys)

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

# Korjattavaa: alkuvaiheessa on kerättävä tieto siitä, millä ID:llä löytyy objektin nimi  ja Customer-attribuutti
# näistä täytyy muodostaa oma dictionarynsa, jota käytetään myöhemmässä vaiheessa.

# 4. Kerää talteen käyttäjätiedot (id ja sähköposti) objektikohtaisesti: objektin nimi, self url ja käyttäjälista
# 5. Hae vastaavat tiedot JSM:n Organisaatioista
# 6. Vertaile näiden kahden välisiä tietoja
# 7. Jos niiden välillä on eroavaisuuksia, päivitä objekti