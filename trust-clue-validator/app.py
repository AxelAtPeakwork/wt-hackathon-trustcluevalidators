import dns.resolver
import json
import logging
from urllib.parse import urlparse
from box import Box
from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS
import requests
from web3 import Web3, HTTPProvider


with open("organization_abi.json", mode="rt", encoding="utf-8") as abi_file:
    ORGANAIZATION_ABI = json.load(abi_file)

with open("trustlinks_abi.json", mode="rt", encoding="utf-8") as abi_file:
    TRUSTLINKS_ABI = json.load(abi_file)
TRUSTLINKS_CONTRACT = "0x059745F23cc4D942BC1C890E7589f7d3A8a3406d"

app = Flask(__name__)
api = Api(app)
CORS(app)
w3 = Web3(HTTPProvider("https://ropsten.infura.io"))

logging.basicConfig()
log = logging.getLogger(__name__)


def fetch_orgid(url):
    response = requests.get(url)
    return response.json()


def getDomainFromOrgIdJson(orgjson):
    orgid = Box(orgjson)
    website_url = urlparse(orgid.hotel.website)
    tld = website_url.netloc.split(".")[-2:]
    tld.insert(0, "_wtaddress")
    return ".".join(tld)


def getDomainWtEntry(domainEntry):
    try:
        myResolver = dns.resolver.Resolver()  # create a new instance named 'myResolver'
        myAnswers = myResolver.query(
            domainEntry, "TXT"
        )  # Lookup the 'A' record(s) for google.com
        return myAnswers[0]
    except Exception as e:
        log.error(e)


def getTrustlinks(sender, receiver):
    trustlinks = w3.eth.contract(address=TRUSTLINKS_CONTRACT, abi=TRUSTLINKS_ABI)
    result = trustlinks.functions.trustLinks(receiver, sender).call()
    trusted = result[0]
    trusted_since_block = result[1]
    return trusted, trusted_since_block


def getDnsTrustClue(organization):
    organization = w3.eth.contract(organization, abi=ORGANAIZATION_ABI)
    orgjson_uri = organization.functions.getOrgJsonUri().call()
    orgjson = fetch_orgid(orgjson_uri)
    domain = getDomainFromOrgIdJson(orgjson)
    wtfingerprint = getDomainWtEntry(domain)
    if wtfingerprint:
        wtfingerprint = wtfingerprint.strings[0].decode("utf-8")
    else:
        wtfingerprint = ""
    owner = organization.functions.owner().call()
    trusted = wtfingerprint.lower() == owner.lower()
    return trusted, domain


class FetchTrustedLinks(Resource):
    def get(self):

        parser = reqparse.RequestParser()
        parser.add_argument("sender", type=str)
        parser.add_argument("receiver", type=str)
        args = parser.parse_args()

        try:
            trusted, trusted_since_block = getTrustlinks(
                args["sender"], args["receiver"]
            )
            return {"trusted": trusted, "trusted_since_block": trusted_since_block}
        except Exception as e:
            log.error(e)


class FetchDnsOwnerClue(Resource):
    def get(self):

        parser = reqparse.RequestParser()
        parser.add_argument("organization", type=str)
        args = parser.parse_args()

        try:
            trusted, dns_record = getDnsTrustClue(args["organization"])
            return {"trusted": trusted, "dns_record": dns_record}
        except Exception as e:
            log.error(e)


class FetchAllClues(Resource):
    def get(self):

        parser = reqparse.RequestParser()
        parser.add_argument("sender", type=str)
        parser.add_argument("receiver", type=str)
        args = parser.parse_args()

        sender = args["sender"]
        receiver = args["receiver"]

        link_result = getTrustlinks(sender, receiver)
        p2ptrust_clue = {
            "trusted": link_result[0],
            "trusted_since_block": link_result[1],
        }

        dns_result = getDnsTrustClue(receiver)
        dns_clue = {"trusted": dns_result[0], "dns_record": dns_result[1]}

        try:

            return {"clues": [{"dns": dns_clue}, {"p2ptrust": p2ptrust_clue}]}
        except Exception as e:
            log.error(e)


api.add_resource(FetchAllClues, "/clues")
api.add_resource(FetchDnsOwnerClue, "/clue/dns")
api.add_resource(FetchTrustedLinks, "/clue/p2ptrust")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
