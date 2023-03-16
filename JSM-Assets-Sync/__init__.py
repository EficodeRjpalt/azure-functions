import logging
from pprint import pprint
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


def get_all_objects(object_ids: list, required_attributes: list) -> list:

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
    attribute_ids_dict = get_attribute_ids(required_attributes, results.json())

    member_attr_id = attribute_ids_dict[getenv('MEMBER_ATTR_NAME')]

    all_objects = []

    for entry in results.json()['objectEntries']:
        entry_attr_ids = [attribute['objectTypeAttributeId'] for attribute in entry['attributes']]
        if member_attr_id in entry_attr_ids:
            all_objects.append(build_assets_object(entry, attribute_ids_dict))

    return {k: v for d in all_objects for k, v in d.items()}


def get_attribute_ids(required_attributes: list, response_body: dict) -> dict:

    attribute_id_dict = {}

    for attribute_info in response_body['objectTypeAttributes']:
        if attribute_info['name'] in required_attributes:
            attribute_id_dict[attribute_info['name']] = attribute_info['id']

    return attribute_id_dict

def build_assets_object(object_entry: dict, attribute_ids_dict: dict) -> dict:
    
    org_name = object_entry['name']
    self_url = object_entry['_links']['self']
    member_attribute = [
        attribute for attribute in object_entry['attributes']
        if attribute['objectTypeAttributeId'] == attribute_ids_dict[getenv('MEMBER_ATTR_NAME')]
    ][0]

    users = [
        {
            'id': user_dict['user']['key'],
            'email': user_dict['user']['emailAddress']
        }
        for user_dict
        in member_attribute['objectAttributeValues']
    ]

    return {
        org_name: {
            "Name": org_name,
            "self": self_url,
            "members": users
        }
    }

def get_jsm_organizations() -> dict:

    servicedesk_id = getenv('SERVICEDESK_ID')
    org_endpoint = getenv('JSM_BASE_URL') + f"rest/servicedeskapi/servicedesk/{servicedesk_id}/organization"

    results = requests.get(
        org_endpoint,
        auth=(
            getenv('EMAIL'),
            getenv('API_TOKEN')
        ),
        timeout=30
    )

    # Tässä pitäisi tarkastaa, että onko paginaation tarvetta.

    orgs = [
        {
            'name': org['name'],
            'id': org['id']
        }
        for org in results.json()['values']
    ]

    return orgs

def get_servicedesk_org_customers(sd_org_dict_list: list) -> dict:

    org_list_w_members = []

    for org_entry in sd_org_dict_list:
        org_id = org_entry['id']
        org_endpoint = getenv('JSM_BASE_URL') + f"rest/servicedeskapi/organization/{org_id}/user"
        results = requests.get(
            org_endpoint,
            auth=(
                getenv('EMAIL'),
                getenv('API_TOKEN')
            ),
            timeout=30
        )

        org_list_w_members.append(
            get_sd_org_object(results.json(), org_entry)
        )

    return {k: v for d in org_list_w_members for k, v in d.items()}


def get_sd_org_object(result_body: dict, org_entry: dict) -> list:

    org_name = org_entry['name']
    org_id = org_entry['id']

    org_members = [
        {
            'id': user_entry['accountId'],
            'email': user_entry['emailAddress']
        }
        for user_entry in result_body['values']
        ]

    org_object = {
        org_name : {
            'name': org_name,
            'id': org_id,
            'members': org_members
        }
    }

    return org_object

def compare_assets_sd_orgs(asset_objects: list, sd_objects: list) -> None:

    orgs_in_assets_and_sd = []

    for sd_org_name in sd_objects.keys():
        if sd_org_name in asset_objects.keys():
            orgs_in_assets_and_sd.append(sd_org_name)
        else:
            logging.info('%s not found in Assets!', sd_org_name)

    for org_name in orgs_in_assets_and_sd:
        compare_member_lists(asset_objects[org_name]['members'], sd_objects[org_name]['members'])
        ## Here: need to build update dispatch information to update objects


def compare_member_lists(asset_member_list: list, sd_member_list: list):

    asset_member_ids = [member['id'] for member in asset_member_list]
    missing_members_list = []

    for sd_member in sd_member_list:
        if sd_member['id'] in asset_member_ids:
            logging.info('%s found in asset member list', sd_member['email'])
        else:
            logging.info('%s not found in asset member list', sd_member['email'])
            missing_members_list.append(sd_member)

    return missing_members_list


def main(req: func.HttpRequest) -> func.HttpResponse:

    dotenv.load_dotenv()
    logging.info('Python HTTP trigger function processed a request.')

    required_attributes = [
        getenv('MEMBER_ATTR_NAME'),
        getenv('NAME_ATTR')
    ]
    
    object_keys = get_all_org_object_keys()
    asset_objects = get_all_objects(object_keys, required_attributes)

    servicedesk_orgs = get_jsm_organizations()
    sd_org_objects = get_servicedesk_org_customers(servicedesk_orgs)

    compare_assets_sd_orgs(asset_objects, sd_org_objects)    

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

# 7. Vertaile näiden kahden välisiä tietoja
#   7.1. Anna listat funktiolle, joka tarkastaa löytyykö portaalin organisaatiot Assetsin puolelta
#   7.2. Jos organisaatiota ei ole Assetsissa -> Älä tee mitään
#   7.3. Jos organisaatio on Assetsissa -> Käydään läpi käyttäjät
# 8. Jos niiden välillä on eroavaisuuksia, päivitä objekti
#   8.1. Funktio, joka luo tietueen, jonka pohjalta ammutaan päivityskäskyjä
# 9. Muuta alun AQL-kysely niin, että objektin tyyppi annetaan .env -tiedostossa

# Muuta: Paginaatio organisaatioille!
# Muuta: Jonnekin täytyy kirjata mitkä skeemat liittyvät mihinkin portaaliin!
# Huomio! Organisaatiot mäpätään VAIN nimen perusteella. Saattaa aiheuttaa ongelmia, sillä ei ole muuta keinoa mäpätä.

# Left off at line 177