import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
from pyserini.search import querybuilder
from pyserini.search import SimpleSearcher
import translators as ts
import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
import xlsxwriter
import json

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

def roundRobin(queries, nrResults):
    hitsMerged = []
    hitsEN = searcherEN.search(buildQuery(queries, 1, 0, 0), k=nrResults)
    hitsES = searcherES.search(buildQuery(queries, 0, 1, 0), k=nrResults)
    hitsDE = searcherDE.search(buildQuery(queries, 0, 0, 1), k=nrResults)
    
    for (en,es,de) in list(zip(hitsEN, hitsES, hitsDE)):
        hitsMerged.append({'docid': en.docid, 'score': en.score})
        hitsMerged.append({'docid': es.docid, 'score': es.score})
        hitsMerged.append({'docid': de.docid, 'score': de.score})

    return hitsMerged

def rawScoring(queries, nrResults):
	hitsMerged = []
	hits = searcherEN.search(buildQuery(queries, 1, 0, 0), k=nrResults)
	for i in range(len(hits)):
		hitsMerged.append({'docid': hits[i].docid, 'score': hits[i].score})

	hits = searcherES.search(buildQuery(queries, 0, 1, 0),k=nrResults)
	for i in range(len(hits)):
		hitsMerged.append({'docid': hits[i].docid, 'score': hits[i].score})

	hits = searcherDE.search(buildQuery(queries, 0, 0, 1), k=nrResults)
	for i in range(len(hits)):
		hitsMerged.append({'docid': hits[i].docid, 'score': hits[i].score})
	
	hitsMergedSorted = sorted(hitsMerged, key = lambda i: i['score'], reverse=True)

	return hitsMergedSorted
		
def rawScoringNormalized(queries, nrResults):
	hitsMerged = []
	hits = searcherEN.search(buildQuery(queries, 1, 0, 0), k=nrResults)
	maxScore = hits[0].score
	for i in range(len(hits)):
		score = hits[i].score / maxScore
		hitsMerged.append({'docid': hits[i].docid, 'score': score})

	hits = searcherES.search(buildQuery(queries, 0, 1, 0),k=nrResults)
	maxScore = hits[0].score
	for i in range(len(hits)):
		score = hits[i].score / maxScore
		hitsMerged.append({'docid': hits[i].docid, 'score': score})

	hits = searcherDE.search(buildQuery(queries, 0, 0, 1), k=nrResults)
	maxScore = hits[0].score
	for i in range(len(hits)):
		score = hits[i].score / maxScore
		hitsMerged.append({'docid': hits[i].docid, 'score': score})
	
	hitsMergedSorted = sorted(hitsMerged, key = lambda i: i['score'], reverse=True)
	
	return hitsMergedSorted

def singleIndex(queries, nrResults):
    hitsMerged = []
    hits = searcher.search(buildQuery(queries, 1, 1, 1), k=nrResults)
    
    for hit in hits:
        hitsMerged.append({'docid': hit.docid, 'score': hit.score})

    return hitsMerged

def englishMultiIndex(queries, nrResults):
	hitsMerged = []
	hits = searcher.search(buildQuery(queries, 1, 0, 0), k=nrResults)

	for hit in hits:
		hitsMerged.append({'docid': hit.docid, 'score': hit.score})

	return hitsMerged

def calcMAP(query, results):
	ap = 0
	relevant = 0
	for i in range(len(results)):
		if query in results[i]["docid"]:
			relevant = relevant + 1
			ap = ap + relevant / (i+1)
	MAP = 1 / int(categoriesDict[query]) * ap

	return MAP

# Main code
searcher = SimpleSearcher('indexes/collection_documents_jsonl')
searcherEN = SimpleSearcher('indexes/collection_documents_EN')
searcherES = SimpleSearcher('indexes/collection_documents_ES')
searcherDE = SimpleSearcher('indexes/collection_documents_DE')

categoriesDict = {}
categories = []
file = open("relevant_documents_per_category.txt", 'r')
lines = file.read().splitlines()
for line in lines:
    k, v = line.split(" : ")
    categoriesDict[k] = v
    categories.append(k)
file.close

nrResults = 30

# Write evaluation to workbook
workbook = xlsxwriter.Workbook('Evaluation.xlsx')
worksheet = workbook.add_worksheet()

worksheet.write(1,0, "Category")
worksheet.write(1,1, "Total pages")

worksheet.write(0,2, "RR")
worksheet.write(0,4, "RS")
worksheet.write(0,6, "NRS")
worksheet.write(0,8, "SI")

worksheet.write(1,2, "MRD")
worksheet.write(1,3, "MT")
worksheet.write(1,4, "MRD")
worksheet.write(1,5, "MT")
worksheet.write(1,6, "MRD")
worksheet.write(1,7, "MT")
worksheet.write(1,8, "MRD")
worksheet.write(1,9, "MT")

worksheet.write(1,10, "English en,es,de-collection")

for i in range(len(categories)):
	query = categories[i]
	worksheet.write(i+2,0, query)
	worksheet.write(i+2,1, categoriesDict[query])

	try:
		queries_words, queries_phrase = get_queries(query)

		results = roundRobin(queries_words, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,2, MAP)

		results = roundRobin(queries_phrase, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,3, MAP)	

		results = rawScoring(queries_words, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,4, MAP)

		results = rawScoring(queries_phrase, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,5, MAP)

		results = rawScoringNormalized(queries_words, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,6, MAP)

		results = rawScoringNormalized(queries_phrase, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,7, MAP)

		results = singleIndex(queries_words, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,8, MAP)

		results = singleIndex(queries_phrase, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,9, MAP)

		results = englishMultiIndex(queries_words, nrResults)
		MAP = calcMAP(query, results)
		worksheet.write(i+2,10, MAP)

		print(i)

	except:
		worksheet.write(i+2,2, "Null")
		worksheet.write(i+2,3, "Null")
		worksheet.write(i+2,4, "Null")
		worksheet.write(i+2,5, "Null")
		worksheet.write(i+2,6, "Null")
		worksheet.write(i+2,7, "Null")
		worksheet.write(i+2,8, "Null")
		worksheet.write(i+2,9, "Null")
		print("Error")

workbook.close()