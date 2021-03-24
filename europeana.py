import secrets

import rdflib
import requests

def wikidata_to_lucene(qid: str) -> str:
    r = requests.get('https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&utf8=1&props=labels|aliases&ids={}'.format(qid))
    parsed_json = r.json()
    item = parsed_json['entities'][qid]

    unique_names = set()

    for _, value in item['labels'].items():
        unique_names.add(value['value'])

    for _, value in item['aliases'].items():
        for value2 in value:
            unique_names.add(value2['value'])

    return '("{}")'.format('" OR "'.join(unique_names))

class Europeana:
    def __init__(self, api_key='api2demo') -> None:
        self.api_key = api_key
        self.search_endpoint = 'https://www.europeana.eu/api/v2/search.json?wskey={}'.format(api_key)
        self.headers = { 'Content-type': 'application/json' }

    def _make_search(self, query: str, query_filters=[], cursor='*', profile='standard', rows=1, sort=[]):
        data = {
            'query': query,
            'rows': str(rows),
            'cursor': cursor,
            'profile': [profile],
            'qf': query_filters,
            'sort': sort,
        }

        r = requests.post(self.search_endpoint, headers=self.headers, json=data)
        return r.json()

    def _make_facetted_search(self, field: str, query='*', offset=0, limit=100):
        data = {
            'facet': [field],
            'query': query,
            'rows': str(0),
            'profile': ['facets'],
            'f.{}.facet.limit'.format(field): str(limit),
            'f.{}.facet.offset'.format(field): str(offset),
        }

        r = requests.post(self.search_endpoint, headers=self.headers, json=data)
        return r.json()

    def search(self, query='*', query_filters=[], profile='standard', sort=[]):
        has_more = True
        cursor = '*'
        while has_more:
            data = self._make_search(query=query, query_filters=query_filters, profile=profile, cursor=cursor, sort=sort)
            try:
                for item in data['items']:
                    yield item
            except KeyError:
                raise ValueError(data['error'])

            if 'nextCursor' in data:
                cursor = data['nextCursor']
            else:
                has_more = False

    def facet(self, field, query='*'):
        raise NotImplementedError

    def exists(self, identifier: str):
        # HTTP HEAD
        raise NotImplementedError

    def random_records(self, query='*', seed=None, return_parsed=True):
        if seed:
            random_seed = 'random_{}'.format(seed)
        else:
            random_seed = 'random_{}'.format(secrets.token_urlsafe(16))

        # europeana_id is needed as Solr needs an uniqueKey field as tie breaker for cursor pagination
        for record in self.search(query=query, profile='minimal', sort=[random_seed, 'europeana_id']):
            if not return_parsed:
                yield 'https://data.europeana.eu/item' + record['id']
            else:
                yield self.resolve(record['id'])

    def resolve(self, uri: str):
        graph = rdflib.Graph()
        return graph.parse(uri, format='application/rdf+xml')

    def resolve_item_by_thumbnail(self, thumbnail: str):
        image = thumbnail.split('uri=')[1].replace('&type=IMAGE-1', '') # todo this assumes the uri parameter is the last one
        query = 'provider_aggregation_edm_isShownBy:"{}"'.format(image) # while this works for SOCH data in won't work in many other cases
        try:
            record = self._make_search(query=query, profile='minimal', rows=1)['items'][0]
        except KeyError:
            return
        except IndexError:
            return
        return self.resolve(record['id'])

    def userset(self, identifier: str, return_parsed=True):
        url = 'https://api.europeana.eu/set/{}?wskey={}&profile=standard'.format(identifier, self.api_key)

        r = requests.get(url)
        data = r.json()
        for item in data['items']:
            if return_parsed:
                yield self.resolve(item)
            else:
                yield item