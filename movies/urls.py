from django.urls import path
from .views import RegisterAPIView, MovieListView, CollectionView
from .middleware import RequestCountView, ResetRequestCountView

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('movies/', MovieListView.as_view(), name='movie-list'),
    path('collection/<uuid:collection_uuid>', CollectionView.as_view(), name='collection-detail'),
    path('collection/', CollectionView.as_view(), name='collection-list'),
    path('request-count/', RequestCountView.as_view(), name='request_count'),
    path('request-count/reset/', ResetRequestCountView.as_view(), name='reset_request_count'),
]