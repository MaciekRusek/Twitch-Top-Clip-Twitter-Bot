import requests
import configparser
import pandas as pd
import json
import urllib.request
from datetime import datetime, timezone

config = configparser.RawConfigParser()
config.read('config.ini')

# Twitter
api_key = config['twitter']['api_key']
api_key_secret = config['twitter']['api_key_secret']

access_token = config['twitter']['access_token']
access_token_secret = config['twitter']['access_token_secret']
bearer_token = config['twitter']['bearer_token']

# Twitch
client_id = config['twitch']['client_id']
client_secret = config['twitch']['client_secret']

base_url = 'https://api.twitch.tv/helix'
auth_url = 'https://id.twitch.tv/oauth2/token'

AuthParams = {'client_id': client_id,
              'client_secret': client_secret,
              'grant_type': 'client_credentials'
              }

AUTCALL = requests.post(url=auth_url, params=AuthParams)
access_token_twitch = AUTCALL.json()['access_token']
HEADERS = {'Client-Id': client_id, 'Authorization': "Bearer " + access_token_twitch}


user_url = f'{base_url}/users?login=popo'
response = requests.get(url=user_url, headers=HEADERS)
user_id = response.json()['data'][0]['id']

# Początek dnia 
date_start = datetime.now(timezone.utc)
date_start = date_start.replace(hour=0, minute=0, second=0)
date_start = date_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]+"Z"

# Koniec dnia
date_end = datetime.now(timezone.utc)
date_end = date_end.replace(hour=23, minute=59, second=59)
date_end = date_end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]+"Z"


clip_url = f'{base_url}/clips?broadcaster_id={user_id}&started_at={date_start}&ended_at={date_end}&first=1'
response = requests.get(url=clip_url, headers=HEADERS)
thumbnail_url = response.json()['data'][0]['thumbnail_url']
title = response.json()['data'][0]['title']
view_count = response.json()['data'][0]['view_count']


mp4_url = thumbnail_url.split("-preview",1)[0] + ".mp4"
out_filename = title[:-1] + ".mp4"
output_path = '/home/maciek/proj/twitterBOT/' + out_filename

urllib.request.urlretrieve(mp4_url, output_path)
