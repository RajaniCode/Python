# Django-app-1
from django.conf.urls import url
# Django-app-3
from . import views
app_name = 'polls'
# Django-app-4
urlpatterns = [
    # ex: /polls/
    url(r'^$', views.IndexView.as_view(), name='index'),
    # ex: /polls/1/
    url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
    # ex: /polls/1/results/
    url(r'^(?P<pk>[0-9]+)/results/$', views.ResultsView.as_view(), name='results'),
    # ex: /polls/1/vote/
    url(r'^(?P<question_id>[0-9]+)/vote/$', views.vote, name='vote'),
    # added the word 'specifics'
    # ex: /polls/specifics/1/
    # url(r'^specifics/(?P<question_id>[0-9]+)/$', views.detail, name='detail'),
]