import requests
import configparser
import urllib.request
from datetime import datetime, timedelta, timezone

class TwitchClip:
    def __init__(self):
        self.config = configparser.RawConfigParser()
        self.config.read('config.ini')
    
        self.client_id = self.config['twitch']['client_id']
        self.client_secret = self.config['twitch']['client_secret']

        self.base_url = 'https://api.twitch.tv/helix'
        self.auth_url = 'https://id.twitch.tv/oauth2/token'
        self.streamers = 'streamer_list.txt'

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
            output_path = '/home/maciek/proj/twitterBOT/clips/' + out_filename
            urllib.request.urlretrieve(mp4_url, output_path)

if __name__ == "__main__":
    twitch_clip = TwitchClip()
    twitch_clip.get_twitch_clips()
