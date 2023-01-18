from requests_oauthlib import OAuth1
import requests
import tweepy
import os
import configparser
import urllib.request
from datetime import datetime, timedelta, timezone
import sys
import time
import json

MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'

class TwitchClip:
    """Sprawdza najpopularniejszego clipa streamera, wybiera 3 najpopularniejsze clipy."""
    def __init__(self):
        self.config = configparser.RawConfigParser()
        self.config.read('config.ini')
    
        self.client_id = self.config['twitch']['client_id']
        self.client_secret = self.config['twitch']['client_secret']

        self.base_url = 'https://api.twitch.tv/helix'
        self.auth_url = 'https://id.twitch.tv/oauth2/token'
        self.streamers = 'streamer_list.txt'
        self.path = '/home/maciek/proj/twitterBOT/clips/'


        self.AuthParams = {'client_id': self.client_id,
                           'client_secret': self.client_secret,
                           'grant_type': 'client_credentials'}

        self.AUTCALL = requests.post(url=self.auth_url, params=self.AuthParams)
        self.access_token_twitch = self.AUTCALL.json()['access_token']
        self.HEADERS = {'Client-Id': self.client_id, 'Authorization': "Bearer " + self.access_token_twitch}
    
    
    def get_yesterday_date_and_format(self):
        # Początek dnia 
        date_start = datetime.now(timezone.utc)
        date_start -= timedelta(days=1)
        date_start = date_start.replace(hour=0, minute=0, second=0)
        date_start = date_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]+"Z"

        # Koniec dnia
        date_end = datetime.now(timezone.utc)
        date_end -= timedelta(days=1)
        date_end = date_end.replace(hour=23, minute=59, second=59)
        date_end = date_end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]+"Z"
        
        return date_start, date_end
        
    def get_twitch_clips(self):
        viewrs_dict = dict()
        urls_dict = dict()
        
        date_start, date_end = self.get_yesterday_date_and_format()
        
        with open(self.streamers, 'r') as streamers:
            for streamer in streamers:
                user_url = f'{self.base_url}/users?login={streamer.strip()}'
                response = requests.get(url=user_url, headers=self.HEADERS)
                user_id = response.json()['data'][0]['id']

                clip_url = f'{self.base_url}/clips?broadcaster_id={user_id}&started_at={date_start}&ended_at={date_end}&first=1'
                response = requests.get(url=clip_url, headers=self.HEADERS)

                if len(response.json()['data']) != 0:
                        
                        view_count = response.json()['data'][0]['view_count']
                        thumbnail_url = response.json()['data'][0]['thumbnail_url']
                        title = response.json()['data'][0]['title']
                        
                        viewrs_dict[streamer.strip()] = view_count
                        urls_dict[streamer.strip()] = [thumbnail_url, title]

        count_viewrs_sorted_max_3 = dict(sorted(viewrs_dict.items(), key=lambda x:x[1], reverse=True)[0:3])
        
        for streamer, viewrs in count_viewrs_sorted_max_3.items():
            thumbnail_url = urls_dict[streamer][0]
            title = urls_dict[streamer][1]

            mp4_url = thumbnail_url.split("-preview",1)[0] + ".mp4"
            out_filename = f'{streamer} {viewrs} {title[:-1]}.mp4'
            output_path = self.path + out_filename
            urllib.request.urlretrieve(mp4_url, output_path)

        return self.path
        
    def get_streamers(self):
        streamer_url = f'{self.base_url}/streams?language=pl'
        response = requests.get(url=streamer_url, headers=self.HEADERS)
        data = response.json()['data']

        for i in range(len(data)):
            print(data[i]['user_name'])
            
    
class TwitterBot:
    def __init__(self, path):
        self.config = configparser.RawConfigParser()
        self.config.read('config.ini')
                
        self.api_key = self.config['twitter']['api_key']
        self.api_key_secret = self.config['twitter']['api_key_secret']        
                
        self.access_token = self.config['twitter']['access_token']
        self.access_token_secret = self.config['twitter']['access_token_secret']
        
        self.path = path
        self.media_url = 'https://upload.twitter.com/1.1/media/upload.json'
        self.post_url = 'https://api.twitter.com/1.1/statuses/update.json'

        os.chdir(self.path)

        self.oauth = OAuth1(self.api_key,
            client_secret=self.api_key_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret)
    
        self.video_filename = None
        self.total_bytes = None
        self.media_id = None
        self.processing_info = None
        self.id_tweet = None
    
    def initiation(self, video):
        self.video_filename = video
        self.total_bytes = os.path.getsize(self.video_filename)
        self.media_id = None
        self.processing_info = None
        
    def upload_init(self):
        request_data = {
            'command': 'INIT',
            'media_type': 'video/mp4',
            'total_bytes': self.total_bytes,
            'media_category': 'tweet_video'
        }

        response = requests.post(url=self.media_url, data=request_data, auth=self.oauth)
        media_id = response.json()['media_id']

        self.media_id = media_id

    def upload_append(self):
        
        segment_id = 0
        bytes_sent = 0
        file = open(self.video_filename, 'rb')

        while bytes_sent < self.total_bytes:
            chunk = file.read(4*1024*1024)

            request_data = {
                'command': 'APPEND',
                'media_id': self.media_id,
                'segment_index': segment_id
            }
            files = {
                'media':chunk
            }

            response = requests.post(url=self.media_url, data=request_data, files=files, auth=self.oauth)

            if response.status_code < 200 or response.status_code > 299:
                print(response.status_code)
                print(response.text)
                sys.exit(0)

            segment_id = segment_id + 1
            bytes_sent = file.tell()

        print('Complete upload.')

    def upload_finalize(self):

        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        response = requests.post(url=self.media_url, data=request_data, auth=self.oauth)
        print(response.json())

        self.processing_info = response.json().get('processing_info', None)
        self.check_status()

    def check_status(self):
        if self.processing_info is None:
            return

        state = self.processing_info['state']

        if state == u'succeeded':
            return

        if state == u'failed':
            sys.exit(0)

        check_after_secs = self.processing_info['check_after_secs']
        
        time.sleep(check_after_secs)

        request_params = {
        'command': 'STATUS',
        'media_id': self.media_id
        }

        response = requests.get(url=self.media_url, params=request_params, auth=self.oauth)
        
        self.processing_info = response.json().get('processing_info', None)
        self.check_status()

    def tweet(self):
        
        print(self.video_filename)
        
        
        
        if self.id_tweet is None:
            request_data = {
                'status': 'Test',
                'media_ids': self.media_id
            }
            response = requests.post(url=self.post_url, data=request_data, auth=self.oauth)
            self.id_tweet = response.json()['id']
        else:
            request_data = {
                'status': 'Test',
                'in_reply_to_status_id': self.id_tweet,
                'media_ids': self.media_id
            }
            response = requests.post(url=self.post_url, data=request_data, auth=self.oauth)
            
   
            
if __name__ == "__main__":
    twitch_clip = TwitchClip()
    twitch_clip.get_streamers()
    path = twitch_clip.get_twitch_clips()
    
    twitter_bot = TwitterBot(path)
    for clip in os.listdir(path):
        twitter_bot.initiation(clip)
        twitter_bot.upload_init()
        twitter_bot.upload_append()
        twitter_bot.upload_finalize()
        twitter_bot.tweet()