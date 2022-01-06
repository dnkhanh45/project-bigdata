import requests
import json
from hdfs import InsecureClient
from elasticsearch import Elasticsearch
from pyspark.sql import SparkSession
from pyspark.sql import SQLContext
from pyspark.sql import Row
import pyspark.sql.functions as F
import pyspark.sql.types as T

def string_to_list(string):
    if string == 'N/A':
        return []
    return [s.strip() for s in string.split(',')]

def convert_votes(vote):
    return int(vote.replace(',', ''))

def convert_boxoffice(boxoffice):
    if boxoffice.startswith('$'):
        return int(boxoffice[1:].replace(',', ''))
    return None

def convert_runtime(runtime):
    if runtime.endswith(' min'):
        return int(runtime[:-4])
    return None

def convert_year(year):
    today = 2021
    if len(year) == 4:
        return [year]
    elif len(year) == 5:
        start_year = int(year[:4])
        return [str(y) for y in range(start_year, today + 1)]
    elif len(year) == 9:
        start_year, end_year = [int(y) for y in year.split('–')[:2]]
        return [str(y) for y in range(start_year, end_year + 1)]
    return []

def es_transform(data):
    result = dict()
    for key in data.keys():
        result[key] = None
        if key in ['Genre', 'Director', 'Writer', 'Actors', 'Language', 'Country']:
            try:
                result[key] = string_to_list(data[key])
            except:
                pass
        elif key == 'Year':
            try:
                result[key] = convert_year(data[key])
            except:
                pass
        elif key in ['Metascore', 'imdbRating']:
            try:
                result[key] = float(data[key])
            except:
                pass
        elif key == 'imdbVotes':
            try:
                result[key] = convert_votes(data[key])
            except:
                pass
        elif key == 'Runtime':
            try:
                result[key] = convert_runtime(data[key])
            except:
                pass
        elif key == 'totalSeasons':
            try:
                result[key] = int(data[key])
            except:
                pass
        elif key == 'totalSeasons':
            try:
                result[key] = int(data[key])
            except:
                pass
        elif key == 'BoxOffice':
            try:
                result[key] = convert_boxoffice(data[key])
            except:
                pass
        else:
            try:
                raw = data[key]
                if raw == 'N/A':
                    result[key] = None
                else:
                    result[key] = raw
            except:
                pass
    return result

def hadoop_transform(load_dict):
    transform_dict = {
        'imdbID': load_dict['imdbID'],
        'Year': load_dict['Year'],
        'Genre': load_dict['Genre'],
        'Director': load_dict['Director'],
        'Writer': load_dict['Writer'],
        'Actors': load_dict['Actors'],
        'Language': load_dict['Language'],
        'Country': load_dict['Country'],
        'Type': load_dict['Type'],
        'imdbRating': float(load_dict['imdbRating'])
    }
    return Row(**transform_dict)

if __name__ == '__main__':
    URL = "https://movie-database-imdb-alternative.p.rapidapi.com/"
    HEADERS = {
        'x-rapidapi-host': "movie-database-imdb-alternative.p.rapidapi.com",
        'x-rapidapi-key': "" # your secret key
    }
    CLIENT_HDFS = InsecureClient('http://namenode:9870', user='root')
    RAW_DATA_DIRECTORY = '/user/root/test/'
    ES = Elasticsearch('elasticsearch:9200')
    INDEX = 'film'
    CLIENT_HDFS.makedirs(RAW_DATA_DIRECTORY)
    if not ES.indices.exists(index=INDEX):
        ES.indices.create(index=INDEX)
    MAX_PAGE_NUMBER = 5
    with open('/content/keyword.txt', 'r') as f:
        SUB_STRING = [line[:-1] if line.endswith('\n') else line for line in f.readlines()]
    print(SUB_STRING)
    count = 0
    for i, sub_string in enumerate(SUB_STRING[:]):
        for j in range(MAX_PAGE_NUMBER):
            search_films_querystring = {
                "s": sub_string,
                "r": "json",
                "page": str(j + 1)
            }
            search_films_response = requests.request(
                method="GET",
                url=URL,
                headers=HEADERS,
                params=search_films_querystring
            )
            # if response successfully
            if search_films_response.status_code == 200:
                search_films_response_data = search_films_response.json()
                # if response successfully
                if search_films_response_data['Response'] == 'True':
                    film_id_list = [film['imdbID'] for film in search_films_response_data['Search']]

                    for film_id in film_id_list[:]:
                        film_details_querystring = {
                            "r": "json",
                            "i": film_id
                        }
                        film_details_response = requests.request(
                            method="GET",
                            url=URL,
                            headers=HEADERS,
                            params=film_details_querystring
                        )
                        # if response successfully
                        if film_details_response.status_code == 200:
                            film_details_response_data = film_details_response.json()
                            transform_result = es_transform(film_details_response_data)
                            ES.index(index=INDEX, id=transform_result['imdbID'], document=transform_result)
                            # if response successfully
                            if film_details_response_data['Response'] == 'True':
                                try:
                                    file_name = film_details_response_data['imdbID'] + '.json'
                                    with CLIENT_HDFS.write(RAW_DATA_DIRECTORY + file_name, encoding='utf-8') as writer:
                                        json.dump(film_details_response_data, writer)
                                    count += 1
                                except Exception as e:
                                    # print(e)
                                    pass
        print('%d/%d'%(i + 1, len(SUB_STRING)))
    print('Crawl %d films'%(count))

    spark = SparkSession.builder.appName("Crawl And Transform").getOrCreate()
    sc = spark.sparkContext
    sqlContext = SQLContext(sc)
    rdd = sc.wholeTextFiles('hdfs://namenode:9000' + RAW_DATA_DIRECTORY + '*.json')
    PROCESSED_DATA_DIRECTORY = '/user/root/dataframe/'
    CLIENT_HDFS.makedirs(PROCESSED_DATA_DIRECTORY)

    transform_rdd = rdd.values() \
                    .map(lambda x: json.loads(x)) \
                    .filter(lambda x: x['imdbRating'] != 'N/A') \
                    .map(lambda x: hadoop_transform(x))
    df = spark.createDataFrame(transform_rdd)
    df.write.save('hdfs://namenode:9000' + PROCESSED_DATA_DIRECTORY, format='parquet', mode='append')
    CLIENT_HDFS.delete(RAW_DATA_DIRECTORY, recursive=True)
