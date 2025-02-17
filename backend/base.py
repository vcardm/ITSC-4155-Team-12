from flask import Flask
from flask import request
import pandas as pd
import json
import pickle 
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np 
import requests  
import os
from pymongo import MongoClient
from mongoengine import connect, StringField, IntField, ListField, Document, BinaryField
import bcrypt 
import jwt 
from flask_jwt_extended import create_access_token, jwt_required
from flask import jsonify, request 
import datetime #think needed for token?
from uuid import uuid4



movie_data = pd.read_csv("final_data/new_moviedata.csv")
movie_score = pd.read_csv("final_data/movie_score.csv")

#load the nlp model and the tfid vect 
nlp_model = 'models/nlp_model.pkl'
#open the file in binary format: read
clf = pickle.load(open(nlp_model, 'rb'))
vect = pickle.load(open('models/transform.pkl', 'rb'))

#function for similairty
def create_similarity(data):
    #create the count matrix as cv
    cv = CountVectorizer()
    #create the matrix based on the column comb which is the combination of them all 
    count_matrix = cv.fit_transform(data['all'].values.astype('U'))
    #create the similiaity score matrix 
    similarity = cosine_similarity(count_matrix)
    return data, similarity 

#recommendation function-> rec
def rec(m, data): #movies -> m
    m = m.lower() #make the movies lowercase 
    data, similarity = create_similarity(data)
    #if the movie title is not there, then return sorry :(
    if m not in data['movie_title'].unique(): 
        return('The movie you requested is not in our database, sorry!')
    else: 
        #now when movie is found
        i = data.loc[data['movie_title']==m].index[0]
        m_list = list(enumerate(similarity[i]))
        m_list = sorted(m_list, key = lambda x:x[1], reverse = True)
        #the list is ten movies but we exclude the first itme since it is the one being requested
        m_list = m_list[1:11]
        #create empty array to add the movie titles 
        l = []
        for i in range(len(m_list)):
            u =m_list[i][0]
            l.append(data['movie_title'][u])
        return l 

#convert list of string to just a list -> ["abc", "def"]
def convert_to_list(my_list):
    my_list = my_list.split(' ","') 
    #replacing the brackets []
    my_list[0] = my_list[0].replace('["', '')
    my_list[-1] = my_list[-1].replace('"]', '')
    return my_list 

api = Flask(__name__)

#for user db 
client = MongoClient("mongodb://localhost:27017")
db = client.users

connect('users')
# user model created 
class User(Document):
    first_name = StringField(required = True)
    last_name = StringField(required = False)
    email = StringField(required = True, unique = True)
    password_hash = BinaryField(required=True)
    token = StringField()

    def set_password(self, password):
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password_bytes, salt)

    def check_password(self, password):
        password_bytes = password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, self.password_hash)

    movie = ListField(StringField())

    ##example usage: 
    # 1. create a new user object and set the password 
    # new_user = User(first_name = 'John', last_name = 'Wick', email = 'johnwick@gmail.com')
    # new_user.set_password('password')
    # #save the user to the db 
    # new_user.save()

    # #2. retrieve the user based on their token
    # retrieved_user = User.objects(token = new_user.token).first()
      
cursor = User.objects(email='a@gmail.com').first()
print(cursor.check_password('a'))

#tmdb api connect
TMDB_API_KEY = "21742194230c942f4f9ca9b6b7e27659"
API_KEY = os.environ.get("TMDB_API_KEY")

if API_KEY is None:
    print("API_KEY environment variable is not set.")
    exit()

@api.route('/search-prod-info')
def search_prod_info():

    query = request.args.get('query', default=None, type=str)
    
    #Since everything in the dataframe is a float, we have this stupid solution
    if(query.isdigit()):
        query+=".0"

    response_body = {
        'movie_data': {
            'movie_title': [],
            "director_name": [],
            "genres": [],
        },
        'movie_score': {
            'release': []
        },
        'tmdb_info': {
            "overview": [],
            "poster_path": [],
            "streaming_services": []
        }
    }
    
    for column_name in response_body['movie_data']:
        data = movie_data.loc[movie_data[column_name].astype(str).str.lower()==query.lower()]
        if not(data.empty):
            for key in response_body['movie_data']:
                response_body['movie_data'][key].extend(data[key].to_list())


    #call tmdb api to retrieve the additional movie information - streaming services 
    response = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}")
    results = response.json().get('results')

    info = results[0]

    if results:
        #add overview poster and release data to the body 
        response_body['tmdb_info']['overview'] = info.get('overview', '')
        response_body['tmdb_info']['poster_path'] = 'https://image.tmdb.org/t/p/original/'+info.get('poster_path', '')
        response_body['movie_score']['release'] = info.get('release_date', '')
    
        #call the tmdb api to get the atreaming services available
        response = requests.get(f"https://api.themoviedb.org/3/movie/{info['id']}/watch/providers?api_key={API_KEY}")
        providers = response.json().get('results', {}).get('US', {}).get('flatrate', [])
        #add streaming services to the response body 
        response_body['tmdb_info']['streaming_services'] = [provider.get('provider_name', '') + ",\n" for provider in providers]


    similar_films = rec(response_body['movie_data']['movie_title'][0], movie_data)
    similar_films = [word.title() for word in similar_films]

    dog_die_title = "https://www.doesthedogdie.com/dddsearch?q="+query
    dog_die_headers = {"X-API-KEY": '21f1213241afbdfc6c6decf60f2ee241', 'Accept': 'application/json'}
    dog_die_id_res = requests.get(dog_die_title, headers=dog_die_headers)
    dog_die_id = dog_die_id_res.json().get('items')[0].get('id')

    dog_die_media = "https://www.doesthedogdie.com/media/"+str(dog_die_id)
    dog_die_res = requests.get(dog_die_media, headers=dog_die_headers).json()
    topics = [elem.get('topic').get('name').capitalize() for elem in dog_die_res.get('topicItemStats') if elem.get('yesSum')>elem.get('noSum')]

    final_body = json.dumps({
        'title': response_body['movie_data']['movie_title'][0].title(),
        'director': response_body['movie_data']['director_name'][0],
        'genres': response_body['movie_data']['genres'],
        'overview': response_body['tmdb_info']['overview'],
        'poster_path': response_body['tmdb_info']['poster_path'],
        'year': response_body['movie_score']['release'],
        'streaming_services': response_body['tmdb_info']['streaming_services'],
        'similar': similar_films,
        'content_warnings': topics
    })

    return final_body

@api.route('/list-search')
def list_search():

    query = request.args.get('query', default=None, type=str)
    
    #Since everything in the dataframe is a float, we have this stupid solution
    if(query.isdigit()):
        query+=".0"
    
    titles = movie_data[movie_data.movie_title.str.contains(query.lower())]['movie_title'].values.tolist()[:20]
    print(titles)
    
    poster_paths = []
    for title in titles:
        response = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={title}")
        results = response.json().get('results')
        
        if len(results)>0:
            info = results[0]

            if(info.get('poster_path')):
                url = 'https://image.tmdb.org/t/p/original/'+info.get('poster_path')
                poster_paths.append(url)
        
        else:
            poster_paths.append('https://user-images.githubusercontent.com/24848110/33519396-7e56363c-d79d-11e7-969b-09782f5ccbab.png')


    response_body = json.dumps({
        'titles': titles,
        'poster_paths': poster_paths,
    })

    return response_body

@api.route('/get-page')
def get_page():
    
    page_num = request.args.get('page_num', type=int)
    page_length = int(request.args['page_length'])

    total_pages = len(movie_data)/page_length

    #Make sure page num is within the max pages
    if(page_num>=total_pages):
        page_num = int(total_pages-1)

    start_index = page_length*page_num
    end_index = (page_length*page_num)+page_length

    titles = movie_data['movie_title'].values.tolist()
    for index, title in enumerate(titles):
        titles[index] = title.title()

    page_titles = titles[start_index:end_index]
    
    poster_paths = []
    for title in page_titles:
        response = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={title}")
        results = response.json().get('results')
        
        if len(results)>0:
            info = results[0]

            if(info.get('poster_path')):
                url = 'https://image.tmdb.org/t/p/original/'+info.get('poster_path')
                poster_paths.append(url)
        
        else:
            poster_paths.append('https://user-images.githubusercontent.com/24848110/33519396-7e56363c-d79d-11e7-969b-09782f5ccbab.png')


    response_body = json.dumps({
        'titles': page_titles,
        'poster_paths': poster_paths,
        'length': total_pages
    })

    return response_body

@api.route('/get-film-queue', methods=['POST'])
def get_film_queue():
    token = request.json.get('token', None)

    titles = User.objects(token=token).first().movie

    print(titles)

    poster_paths = []
    for title in titles:
        response = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={title}")
        results = response.json().get('results')
        
        if len(results)>0:
            info = results[0]

            if(info.get('poster_path')):
                url = 'https://image.tmdb.org/t/p/original/'+info.get('poster_path')
                poster_paths.append(url)
        
        else:
            poster_paths.append('https://user-images.githubusercontent.com/24848110/33519396-7e56363c-d79d-11e7-969b-09782f5ccbab.png')

    response_body = json.dumps({
        'titles': titles,
        'posters': poster_paths
    })

    return response_body

# needed for login - token
#verify user credentials
def verify_credientials(username, password):
    # return true if creds are valid flase otherwise
    retrieved_user = User.objects(email=username).first()
    if(retrieved_user):
        if retrieved_user.check_password(password):
            return True
    else:
        return False

# define create_access_token funct
def create_access_token():
    # generate access token using the "identity" provided
    access_token = uuid4()
    return access_token 

@api.route('/signup', methods=["POST"])
def signup():
    name = request.json.get('name', None)
    username = request.json.get('email', None)
    password = request.json.get('password', None)

    if(verify_credientials(username, password)):
        return jsonify({'msg': 'user already in database'}), 401
    else:
        new_user = User(email=username, first_name=name)
        new_user.set_password(password)
        access_token=str(create_access_token())
        new_user.token=access_token
        new_user.save()
        return jsonify(token = access_token), 200

#login route 
@api.route('/login',  methods=["POST"])
def login():
    # get username and password from the request
    username = request.json.get('email', None)
    password = request.json.get('password', None)

    print(username)

    #verify user creds
    if verify_credientials(username, password):
        #generate new access token 
        access_token = User.objects(email=username).first().token
        return jsonify(token = access_token), 200
    else: 
        return jsonify({'msg': "Invalid username or password."}), 401
    

    
# route for adding a film to the queue (requires authentication)
@api.route('/post-film-queue', methods=['POST'])
def post_film_queue():
    title = request.json.get('title', None)
    token = request.json.get('token', None)
    retrieved_user = User.objects(token=token).first()
    retrieved_user.movie.append(title)
    retrieved_user.save()
    print(retrieved_user.movie)
    # replace with your own logic for adding a film to the queue
    return jsonify({'msg': 'Film added to the queue.'}), 200

@api.route('/remove-film-queue', methods=['POST'])
def remove_film_queue():
    title = request.json.get('title', None)
    token = request.json.get('token', None)

    retrieved_user = User.objects(token=token).first()
    retrieved_user.movie.remove(title)
    retrieved_user.save()
    print(retrieved_user.movie)
    # replace with your own logic for adding a film to the queue
    return jsonify({'msg': 'Film added to the queue.'}), 200

@api.route('/post-user-info', methods=['POST'])
def post_user():
    dummy_token = {'token': "12345"}
    return dummy_token

@api.route('/get-profile', methods=['POST'])
def get_profile():
    token = request.json.get('token', None)

    retrieved_user = User.objects(token=token).first()
    fname = retrieved_user.first_name
    lname = retrieved_user.last_name
    email = retrieved_user.email
    movies = retrieved_user.movie

    return {"first_name": fname, "last_name": lname, "email": email, "movie": movies}