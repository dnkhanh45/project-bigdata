from flask import Flask, render_template, request, redirect, jsonify, url_for
from elasticsearch import Elasticsearch
app = Flask(__name__, template_folder='./templates', static_folder='./static')
ES = Elasticsearch('elasticsearch:9200')
INDEX = 'film'
MAX_SIZE = 2000
# @app.route('/')
# def index():
#     return doc['_source']['city']

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        input_id = request.form['name']
        substring = input_id.strip()
        return redirect(url_for('search_result', substring=substring))
    return render_template("index.html")

@app.route("/search/<substring>", methods=["GET", "POST"])
def search_result(substring):
    query = {
        "query_string": {
            "query": "*" + substring +"*",
            "default_field": "Title"
        }
    }
    result = [r['_source'] for r in ES.search(index=INDEX, query=query, size=MAX_SIZE)['hits']['hits']]
    return render_template("search.html", user=result)

@app.route("/details/<id>", methods=["GET", "POST"])
def show_details(id):
    details = ES.get(index=INDEX, id=id)['_source']
    # return jsonify(details)
    should_list = list()
    for key in ['Genre', 'Actors', 'Country', 'Director', 'Language', 'Writer', 'Year']:
        for value in details[key]:
            should_list.append({
                "match_phrase": {
                    key: value
                }
            })
    query = {
        "bool": {
            "should": should_list
        }
    }
    recommend = [r['_source'] for r in ES.search(index=INDEX, size=MAX_SIZE, query=query)['hits']['hits'] if r['_source']['imdbID'] != details['imdbID']]
    return render_template("details.html", main=details, user=recommend)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
    # result = ES.search(index=INDEX)
    # print(result['hits']['hits'][0])
    # query = {
    #     "bool": {
    #         "should": [
    #             {
    #                 "match_phrase": {
    #                     "Genre": "Family"
    #                 }
    #             },
    #             {
    #                 "match_phrase": {
    #                     "Genre": "Comedy"
    #                 }
    #             }
    #         ]
    #     }
    # }
    # print(([r['_source']['Genre'] for r in ES.search(index=INDEX, query=query, size=MAX_SIZE)['hits']['hits']]))
