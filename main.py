from requests_oauthlib import OAuth1
import requests
import os
import configparser
import urllib.request
from datetime import datetime, timedelta, timezone
import sys
import time
import logging

class TwitchClip:
    """Sprawdza najpopularniejszego clipa streamera, wybiera 3 najpopularniejsze clipy."""
    
    logging.basicConfig(filename='logs/Twitch.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    def __init__(self):
        self.config = configparser.RawConfigParser()
        self.config.read('config.ini')
    
        self.client_id = self.config['twitch']['client_id']
        self.client_secret = self.config['twitch']['client_secret']

        self.base_url = 'https://api.twitch.tv/helix'
        self.auth_url = 'https://id.twitch.tv/oauth2/token'
        
        self.streamers = 'streamer_list.txt'
        self.streamers_ids = 'streamer_id_list.txt'
        
        self.views_count = dict()
        self.urls = dict()

        self.path = '/home/maciek/proj/twitterBOT/clips/'

        self.AuthParams = {'client_id': self.client_id,
                           'client_secret': self.client_secret,
                           'grant_type': 'client_credentials'}


        self.AUTCALL = requests.post(url=self.auth_url, params=self.AuthParams)
        self.access_token_twitch = self.AUTCALL.json()['access_token']
        self.HEADERS = {'Client-Id': self.client_id, 'Authorization': "Bearer " + self.access_token_twitch}

    def get_yesterday_date_and_format(self):
        '''Funkcja zwracjąca dwie sformatowane daty z dnia wczorajszego - (Początek dnia, Koniec Dnia)'''
        date_start = datetime.now(timezone.utc)
        date_start -= timedelta(days=1)
        date_start = date_start.replace(hour=0, minute=0, second=0)
        date_start = date_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]+"Z"

        date_end = datetime.now(timezone.utc)
        date_end -= timedelta(days=1)
        date_end = date_end.replace(hour=23, minute=59, second=59)
        date_end = date_end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]+"Z"
        
        logging.info("Complete formating date...")
        return date_start, date_end
        
    def get_twitch_clips(self) -> str:
        """
        Funkcja pobierająca 3 najpopularniejsze clipy z dnia wczorajszego.\n
        Zwraca nam ścieszkę z clipami.
        """
        
        date_start, date_end = self.get_yesterday_date_and_format()
        
        with open(self.streamers_ids, 'r') as streamers:
            for user_id in streamers:
                clip_url = f'{self.base_url}/clips?broadcaster_id={user_id.strip()}&started_at={date_start}&ended_at={date_end}&first=1'
                response = requests.get(url=clip_url, headers=self.HEADERS)

                # Sprawdza czy istnieje jakiś clip
                if len(response.json()['data']) != 0:
                        view_count = response.json()['data'][0]['view_count']
                        
                        thumbnail_url = response.json()['data'][0]['thumbnail_url']
                        title = response.json()['data'][0]['title']
                        streamer = response.json()['data'][0]['broadcaster_name']
                        
                        self.views_count[user_id.strip()] = view_count
                        self.urls[user_id.strip()] = [thumbnail_url, title, streamer]
                
        count_viewrs_sorted_max_3 = dict(sorted(self.views_count.items(), key=lambda x:x[1], reverse=True)[0:3])
        logging.info(f'ended filtering, results: {count_viewrs_sorted_max_3}.')
        
        for id, clip_info in enumerate(count_viewrs_sorted_max_3.items()):
            
            streamer_id, views = clip_info[0], clip_info[1]
            
            thumbnail_url = self.urls[streamer_id][0] 
            title = self.urls[streamer_id][1]
            streamer = self.urls[streamer_id][2]

            # Downloading clip from twitch and save to folder
            mp4_url = thumbnail_url.split("-preview",1)[0] + ".mp4"
            out_filename = f'{id} {streamer} {views} {title}.mp4'            
            output_path = self.path + out_filename
            urllib.request.urlretrieve(mp4_url, output_path)
        logging.info(f'ended downloading clips.')    
        return self.path
    
    def change_streamer_to_id(self):
        """Funkcja pozwalająca na zmianne streamera w id, oraz zapisuje go do pliku."""
        user_ids = []
        with open(self.streamers, 'r') as streamers:
            for streamer in streamers:
                try:        
                    user_url = f'{self.base_url}/users?login={streamer.strip()}'
                    response = requests.get(url=user_url, headers=self.HEADERS)
                    user_ids.append(response.json()['data'][0]['id'])                
                except requests.exceptions.Timeout as errt:
                    logging.error(errt)
                except:
                    logging.error("Erorr while changing streamers to id.")
        with open(self.streamers_ids, "w") as streamers_ids:
            logging.info(f"Move streamer id to file: {self.streamers_ids}.")
            for user in user_ids:
                streamers_ids.write(f'{user}\n')
                 

class TwitterBot:
    """Wysyła clipy do twittera by uzyskać media_id. Clipy wysyła w retweet"""
    
    logging.basicConfig(filename='logs/Twitter.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

    def __init__(self, path):
        self.config = configparser.RawConfigParser()
        self.config.read('config.ini')
                
        self.api_key = self.config['twitter']['api_key']
        self.api_key_secret = self.config['twitter']['api_key_secret']        
                
        self.access_token = self.config['twitter']['access_token']
        self.access_token_secret = self.config['twitter']['access_token_secret']
        
        self.path = path
        os.chdir(self.path)
        
        self.MEDIA_URl = 'https://upload.twitter.com/1.1/media/upload.json'
        self.POST_URL = 'https://api.twitter.com/1.1/statuses/update.json'

        self.oauth = OAuth1(self.api_key, client_secret=self.api_key_secret,
                            resource_owner_key=self.access_token,resource_owner_secret=self.access_token_secret)
        
        self.id_tweet = None
        self.last = None
        
        self.video_filename = None
        self.total_bytes = None
        self.media_id = None
        self.processing_info = None
    
        self.id = None
        self.streamer = None
        self.views = None
        self.title = None
        self.yesterday_date = datetime.now()
        self.yesterday_date -= timedelta(days=1)
        self.yesterday_date = self.yesterday_date.strftime("%Y-%m-%d")

        
    def initiation(self, video):
        """Funkcja pobierająca ważne informacje"""
        self.video_filename = video
        streamer_info = self.video_filename.split(" ")
        self.id = streamer_info[0]
        self.streamer = streamer_info[1]
        self.views = streamer_info[2]
        self.title = " ".join(streamer_info[3:-1]) 
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

        response = requests.post(url=self.MEDIA_URl, data=request_data, auth=self.oauth)
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

            response = requests.post(url=self.MEDIA_URl, data=request_data, files=files, auth=self.oauth)

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

        response = requests.post(url=self.MEDIA_URl, data=request_data, auth=self.oauth)
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

        response = requests.get(url=self.MEDIA_URl, params=request_params, auth=self.oauth)
        
        self.processing_info = response.json().get('processing_info', None)
        self.check_status()

    def tweet(self):
        
        if self.id_tweet is None:
            request_data = {
                'status': f'Najpopularniejszym clipem dnia {self.yesterday_date} był {self.streamer}, z liczbą {self.views} wyświetleń 🤯🔥',
                'media_ids': self.media_id
            }
            response = requests.post(url=self.POST_URL, data=request_data, auth=self.oauth)
            self.id_tweet = response.json()['id']
        else:
            if self.last is None:
                request_data = {
                    'status': f'Na 2 miejscu znalazł się {self.streamer} z liczbą {self.views} wyświetleń 😎',
                    'in_reply_to_status_id': self.id_tweet,
                    'media_ids': self.media_id
                }
                response = requests.post(url=self.POST_URL, data=request_data, auth=self.oauth)
                self.last = True
            else:
                request_data = {
                    'status': f'Na 3 miejscu znalazł się {self.streamer} z liczbą {self.views} wyświetleń 🫡',
                    'in_reply_to_status_id': self.id_tweet,
                    'media_ids': self.media_id
                }
                response = requests.post(url=self.POST_URL, data=request_data, auth=self.oauth)
   
            
if __name__ == "__main__":
    start_time = time.time()
    
    twitch_clip = TwitchClip()
    # twitch_clip.change_streamer_to_id()
    path = twitch_clip.get_twitch_clips()
    
    twitter_bot = TwitterBot(path)
    for clip in os.listdir(path):
        twitter_bot.initiation(clip)
        twitter_bot.upload_init()
        twitter_bot.upload_append()
        twitter_bot.upload_finalize()
        twitter_bot.tweet()
    end_time = time.time() - start_time
    print(f"czas trwania: {end_time} s")