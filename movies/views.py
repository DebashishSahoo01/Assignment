from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .models import Collection,Movie
from django.db import IntegrityError
import os
import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

THIRD_PART_URL = "https://demo.credy.in/api/v1/maya/movies/"

class RegisterAPIView(APIView):
    def post(self,request):
        username=request.data['username']
        password=request.data['password']
        
        if not username or not password:
            return Response({"error":"Username and password are required"},status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken, please choose a different one"}, status=status.HTTP_400_BAD_REQUEST)
        
        user=User.objects.create_user(
            username=username,
            password=password
        )
        user.save()
        refresh=RefreshToken.for_user(user)
        return Response({"message":"User created successfully","refresh":str(refresh),"access":str(refresh.access_token)},status=status.HTTP_201_CREATED)

def fetch_movies_with_retries(url,username, password, params=None, max_retries=3, delay=2):
    attempts=0
    while attempts<max_retries:
        try:
            response = requests.get(url,auth=(username,password),params=params,timeout=10,verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            attempts +=1
            logging.error(f"Attempt {attempts} failed: {str(e)}")
            if attempts==max_retries:
                raise e
            time.sleep(delay)
    
class MovieListView(APIView):
    permission_classes=[IsAuthenticated]
    
    def get(self,request):
        username=os.getenv('MOVIE_API_USERNAME')
        password=os.getenv('MOVIE_API_PASSWORD')
        
        if not username or not password:
            return Response({"error":"Movie API credentials are missing"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        page_number=request.query_params.get('page',1)
        params = {
            'page': page_number
        }
        try:
            data=fetch_movies_with_retries(THIRD_PART_URL,username,password,params=params)
            return Response(data,status=status.HTTP_200_OK)
        except requests.exceptions.RequestException as e:
            return Response({"error": "Movie service unavailable. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CollectionView(APIView):
    permission_classes=[IsAuthenticated]
    def create_movies(self, collection, movies):
        for movie in movies:
            movie_uuid = movie.get('uuid')

            if movie_uuid is not None:
                if Movie.objects.filter(uuid=movie_uuid).exists():
                    logging.warning(f"Movie with UUID {movie_uuid} already exists. Skipping...")
                    continue
            try:
                Movie.objects.create(
                    title=movie['title'],
                    description=movie['description'],
                    genres=movie['genres'],
                    uuid=movie_uuid,
                    collection=collection
                )
            except IntegrityError:
                logging.error(f"IntegrityError when trying to create movie {movie['title']} with UUID {movie_uuid}.")
    def get(self,request,collection_uuid=None):
        if collection_uuid:
            try:
                collection=Collection.objects.get(uuid=collection_uuid,created_by=request.user)
            except Collection.DoesNotExist:
                logging.warning(f"Collection with uuid {collection_uuid} not found for user {request.user}.")
                return Response({"error":"Collection not found"},status=status.HTTP_404_NOT_FOUND)
            movies=collection.movies.all()
            data={
                "title":collection.title,
                "description":collection.description,
                "movies":[{"title":movie.title,"description":movie.description,"genres":movie.genres,"uuid":movie.uuid} for movie in movies]
            }
            return Response(data,status=status.HTTP_200_OK)
        collections=Collection.objects.filter(created_by=request.user)
        fav_genres=self.get_favorite_genres(collections)
        data={
            "collection":[{"title":c.title,"uuid":c.uuid,"description":c.description} for c in collections],
            "favorite_genres":fav_genres
        }
        return Response({"is_success":True,"data":data},status=status.HTTP_200_OK)
    def post(self,request,collection_uuid=None):
        if collection_uuid:
            try:
                collection=Collection.objects.get(uuid=collection_uuid,created_by=request.user)
            except Collection.DoesNotExist:
                logging.warning(f"Collection with uuid {collection_uuid} not found for user {request.user}.")
                return Response({"error":"Collection not found"},status=status.HTTP_404_NOT_FOUND)
            movies=request.data.get("movies")
            if not movies:
                return Response({"error": "Movies data is required"}, status=status.HTTP_400_BAD_REQUEST) 
            self.create_movies(collection,movies)
            return Response({"Message":f"New Movie Added"},status=status.HTTP_201_CREATED)
        collection=Collection.objects.create(
            title=request.data['title'],
            description=request.data['description'],
            created_by=request.user
        )
        movies=request.data.get('movies')
        if not movies:
            return Response({"error": "Movies data is required"}, status=status.HTTP_400_BAD_REQUEST)
        self.create_movies(collection,movies)
        return Response({"collection_uuid":collection.uuid},status=status.HTTP_201_CREATED)
    def put(self,request,collection_uuid):
        if collection_uuid:
            try:
                collection=Collection.objects.get(uuid=collection_uuid,created_by=request.user)
            except Collection.DoesNotExist:
                logging.warning(f"Collection with uuid {collection_uuid} not found for user {request.user}.")
                return Response({"error":"Collection not found"},status=status.HTTP_404_NOT_FOUND)
            title=request.data.get('title',None)
            description=request.data.get('description',None)
            if title:
                collection.title = title
            if description:
                collection.description = description
            movies = request.data.get('movies', None)
            if movies is not None:
                collection.movies.all().delete()
                self.create_movies(collection,movies)
            collection.save()
            return Response({"collection_uuid":collection.uuid,"message":"Collection updated successfully"},status=status.HTTP_200_OK)
        return Response({"error":"Please Provide the collection uuid"},status=status.HTTP_404_NOT_FOUND)
            
    def delete(self,request,collection_uuid):
        if collection_uuid:
            try:
                collection=Collection.objects.get(uuid=collection_uuid,created_by=request.user)
            except Collection.DoesNotExist:
                logging.warning(f"Collection with uuid {collection_uuid} not found for user {request.user}.")
                return Response({"error":"Collection not found"},status=status.HTTP_404_NOT_FOUND)
            collection.delete()
            return Response({"message":"Collection deleted successfully"},status=status.HTTP_204_NO_CONTENT)
        return Response({"error":"Please Provide the collection uuid"},status=status.HTTP_404_NOT_FOUND)
    def get_favorite_genres(self,collections):
        genre_count={}
        for collection in collections:
            for movie in collection.movies.all():
                for genre in map(str.strip, movie.genres.split(',')):
                    if genre:
                        genre_count[genre]=genre_count.get(genre,0)+1
        sorted_genre=sorted(genre_count,key=genre_count.get,reverse=True)
        print(sorted_genre)
        return ", ".join(sorted_genre[:3])    