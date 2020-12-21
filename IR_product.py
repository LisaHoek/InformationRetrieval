import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
from pyserini.search import querybuilder
from pyserini.search import SimpleSearcher
import translators as ts
import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
import enum

#Run this code only once to index and download package
'''
os.system("python3 -m pyserini.index -collection JsonCollection -generator DefaultLuceneDocumentGenerator \
 -threads 1 -input collection_documents_jsonl \
 -index indexes/collection_documents_jsonl -storePositions -storeDocvectors -storeRaw")
os.system("python3 -m pyserini.index -collection JsonCollection -generator DefaultLuceneDocumentGenerator \
 -threads 1 -input collection_documents_EN \
 -index indexes/collection_documents_EN -storePositions -storeDocvectors -storeRaw")
os.system("python3 -m pyserini.index -collection JsonCollection -generator DefaultLuceneDocumentGenerator \
 -threads 1 -input collection_documents_ES \
 -index indexes/collection_documents_ES -storePositions -storeDocvectors -storeRaw")
os.system("python3 -m pyserini.index -collection JsonCollection -generator DefaultLuceneDocumentGenerator \
 -threads 1 -input collection_documents_DE \
 -index indexes/collection_documents_DE -storePositions -storeDocvectors -storeRaw")

nltk.download('punkt')
'''

def get_queries(category_name, source = 'en'):
    languages = [('en', 'english'), ('es', 'spanish'), ('de', 'german')]
    query = category_name.replace("_", " ")
    trans_phrase = {}
    trans_words = {}
    
    for (trans_lang, stop_lang) in languages:
        query_trans_phrase = ts.bing(query, from_language=source, to_language=trans_lang).lower()
        query_trans_words = [ts.bing(token, from_language=source, to_language=trans_lang).lower() for token in word_tokenize(query)]

        query_clean_phrase = [token for token in word_tokenize(query_trans_phrase) if token not in set(stopwords.words(stop_lang))]
        query_clean_words = [token for token in query_trans_words if token not in set(stopwords.words(stop_lang))]
        
        trans_phrase[trans_lang] = query_clean_phrase
        trans_words[trans_lang] = query_clean_words
        
    return (trans_words, trans_phrase)

def buildQuery(queries, en, es, de):
	should = querybuilder.JBooleanClauseOccur['should'].value
	boolean_query_builder = querybuilder.get_boolean_query_builder()
	if en:
		for word in queries["en"]:
			term = querybuilder.get_term_query(word)
			boolean_query_builder.add(term, should)
	if es:
		for word in queries["es"]:
			term = querybuilder.get_term_query(word)
			boolean_query_builder.add(term, should)
	if de:
		for word in queries["de"]:
			term = querybuilder.get_term_query(word)
			boolean_query_builder.add(term, should)
	return boolean_query_builder.build()
		
def rawScoringNormalized(queries, nrResults, dests):
	hitsMerged = []
	if "en" in dests:
		hits = searcherEN.search(buildQuery(queries, 1, 0, 0), k=nrResults)
		maxScore = hits[0].score
		for i in range(len(hits)):
			score = hits[i].score / maxScore
			hitsMerged.append({'docid': hits[i].docid, 'score': score})
	if "es" in dests:
		hits = searcherES.search(buildQuery(queries, 0, 1, 0),k=nrResults)
		maxScore = hits[0].score
		for i in range(len(hits)):
			score = hits[i].score / maxScore
			hitsMerged.append({'docid': hits[i].docid, 'score': score})
	if "de" in dests:
		hits = searcherDE.search(buildQuery(queries, 0, 0, 1), k=nrResults)
		maxScore = hits[0].score
		for i in range(len(hits)):
			score = hits[i].score / maxScore
			hitsMerged.append({'docid': hits[i].docid, 'score': score})
	hitsMergedSorted = sorted(hitsMerged, key = lambda i: i['score'], reverse=True)
	return hitsMergedSorted

def calcMAP(query, results):
	ap = 0
	relevant = 0
	for i in range(len(results)):
		if query in results[i]["docid"]:
			relevant = relevant + 1
			ap = ap + relevant / (i+1)
	MAP = 1 / int(categoriesDict[query]) * ap
	return MAP

def number(question):
    result = input(question)
    while not(result.isdigit() and 1 <= int(result) <= 100):
        print("That is not a valid option. Please try again.")
        result = input(question)
    return result

def languages(question, possible_answers):
    result = input(question)
    while not(result in possible_answers):
        print("That is not a valid option. Please try again.")
        result = input(question)
    return result

class Lang_enum(enum.Enum):
    English = "en"
    Spanish = "es"
    German = "de"

searcher = SimpleSearcher('indexes/collection_documents_jsonl')
searcherEN = SimpleSearcher('indexes/collection_documents_EN')
searcherES = SimpleSearcher('indexes/collection_documents_ES')
searcherDE = SimpleSearcher('indexes/collection_documents_DE')

source = "en"
dests = []
possible_languages = ["en", "de", "es"]

query = input("Enter your English query: ")
nrResults = int(number("How many results do you want: (1-100) "))
for lang in possible_languages:
    if (languages("Do you want results in {} (yes/no): ".format(str(Lang_enum(lang).name)), ["yes", "no"]) == "yes"):
        dests.append(lang)

query_words, query_phrase = get_queries(query)
results = rawScoringNormalized(query_phrase, nrResults, dests)
for i in range(nrResults):
	print(f'{i+1:2} {results[i]["docid"]:15} {results[i]["score"]:.5f}')
