"""Two-step, explicit-class Wikidata queries. No guessed project or status values."""
import re


def ids(class_id,offset=0,limit=500,current_only=False):
    if not re.fullmatch(r'Q[1-9]\d*',class_id) or not 1<=limit<=500 or offset<0:raise ValueError('Bounded class query required')
    lifecycle = '''{ ?item wdt:P729 ?recent FILTER(?recent >= "2020-01-01T00:00:00Z"^^xsd:dateTime) }
 UNION { ?item wdt:P1619 ?recent FILTER(?recent >= "2020-01-01T00:00:00Z"^^xsd:dateTime) }
 UNION { VALUES ?label { "building or structure under construction"@en "proposed building or structure"@en "pre-construction"@en }
 ?state rdfs:label ?label. ?item wdt:P5817 ?state }''' if current_only else ''
    return f'''SELECT DISTINCT ?item WHERE {{ ?item wdt:P31 wd:{class_id}; wdt:P625 ?point . {lifecycle} }} ORDER BY ?item LIMIT {limit} OFFSET {offset}'''


def details(qids):
    if not qids or len(qids)>80 or any(not re.fullmatch(r'Q[1-9]\d*',q) for q in qids):raise ValueError('Use 1–80 explicit QIDs')
    values=' '.join('wd:'+q for q in qids)
    return '''SELECT DISTINCT ?item ?itemLabel ?countryLabel ?countryCode ?coord ?precision ?alias ?instance
 ?statusLabel ?statusDate ?statusStart ?entry ?opening ?retirement ?inception
 ?capacity ?capacityUnitLabel ?cost ?costCurrency ?costDate
 ?owner ?ownerLabel ?operator ?operatorLabel ?developer ?developerLabel ?contractor ?contractorLabel
 WHERE { VALUES ?item { %s }
 { ?item p:P625 ?statement. ?statement ps:P625 ?coord; psv:P625 ?geo; wikibase:rank ?rank.
   FILTER(?rank != wikibase:DeprecatedRank) ?geo wikibase:geoGlobe wd:Q2.
   OPTIONAL { ?geo wikibase:geoPrecision ?precision } }
 UNION { ?item wdt:P17 ?country. ?country wdt:P297 ?countryCode }
 UNION { ?item wdt:P31 ?instance }
 UNION { ?item skos:altLabel ?alias FILTER(LANG(?alias)="en") }
 UNION { ?item p:P5817 ?statement. ?statement ps:P5817 ?status; wikibase:rank ?rank.
   FILTER(?rank != wikibase:DeprecatedRank) OPTIONAL { ?statement pq:P585 ?statusDate }
   OPTIONAL { ?statement pq:P580 ?statusStart } }
 UNION { ?item wdt:P729 ?entry }
 UNION { ?item wdt:P1619 ?opening }
 UNION { ?item wdt:P730 ?retirement }
 UNION { ?item wdt:P571 ?inception }
 UNION { ?item p:P2109/psv:P2109 ?quantity. ?quantity wikibase:quantityAmount ?capacity; wikibase:quantityUnit ?capacityUnit }
 UNION { ?item p:P2130 ?statement. ?statement psv:P2130 ?quantity.
   ?quantity wikibase:quantityAmount ?cost; wikibase:quantityUnit ?costUnit.
   OPTIONAL { ?costUnit wdt:P498 ?costCurrency } OPTIONAL { ?statement pq:P585 ?costDate } }
 UNION { ?item wdt:P127 ?owner }
 UNION { ?item wdt:P137 ?operator }
 UNION { ?item wdt:P178 ?developer }
 UNION { ?item wdt:P1652 ?contractor }
 SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
 } LIMIT 20000''' % values
