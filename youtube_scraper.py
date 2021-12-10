from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup

import aiohttp
import asyncio
import json
import pandas as pd
import re

class YoutubeScraper:
    YOUTUBE_VIDEO_PREFIX = 'https://www.youtube.com/watch?v='
    YOUTUBE_SEARCH_PREFIX = 'https://www.youtube.com/results?search_query='

    def __init__(self, proxy_url=None):
        self.proxy_url = proxy_url
        
    async def get_video(self, session, video_id):
        async with session.get(self.YOUTUBE_VIDEO_PREFIX + video_id) as response:
            return (video_id, await response.text())

    async def get_search(self, session, search_term):
        async with session.get(self.YOUTUBE_SEARCH_PREFIX + search_term) as response:
            return (search_term, await response.text())

    def js_var(self, response, var_name):
        soup = BeautifulSoup(response, 'html.parser')
        scripts = soup.find('body').find_all('script')
        pattern = re.compile(r'= (.*});')

        for script in scripts:
            if str(script) != None and 'var ' + var_name in str(script):
                    return json.loads(pattern.findall((str(script)))[0])

        return None

    async def search_results(self, search_term):
        if self.proxy_url != None:
            session = aiohttp.ClientSession(connector=ProxyConnector.from_url(self.proxy_url))
        else:
            session = aiohttp.ClientSession()

        # Get search response
        response = (await (self.get_search(session, search_term)))[1]
        await session.close()

        initial_data = self.js_var(response, 'ytInitialData')

        # Recommendations count index is variable; we find it here before trying to access
        recommendations_index = 0
        recommendations_key = initial_data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']

        for item in recommendations_key:
            if 'videoRenderer' in item['itemSectionRenderer']['contents'][0] or \
                len(item['itemSectionRenderer']['contents']) > 15: # Promotional slots have relatively few items in each section
                break
            recommendations_index += 1

        recommendations = []
        
        for recommendation in recommendations_key[recommendations_index]['itemSectionRenderer']['contents']:
            try:
                recommendations.append(recommendation['videoRenderer']['videoId'])
            except KeyError as e:
                if e.args[0] == 'videoRenderer':
                    pass

        return recommendations

    def video_recommendations(self, initial_data):
        recommendations_list = initial_data['contents']['twoColumnWatchNextResults']['secondaryResults']['secondaryResults']['results']
        recommendations = []
        for recommendation in recommendations_list:
            if 'compactVideoRenderer' in recommendation:
                recommendations.append(recommendation['compactVideoRenderer']['videoId'])
        return recommendations

    def video_is_playable(self, initial_player_response):
        return initial_player_response['playabilityStatus']['status'] in ['OK', 'LOGIN_REQUIRED']

    def video_is_private(self, initial_player_response):
        return initial_player_response['playabilityStatus']['status'] == 'LOGIN_REQUIRED'

    def video_is_removed(self, initial_player_response):
        try:
            return initial_player_response['playabilityStatus']['reason'] == 'This video has been removed for violating YouTube\'s Community Guidelines.'
        except KeyError as e:
            if e.args[0] == 'reason':
                return False

    def video_requires_payment(self, initial_player_response):
        try:
            return initial_player_response['playabilityStatus']['reason'] == 'This video requires payment to watch.'
        except KeyError as e:
            if e.args[0] == 'reason':
                return False

    def video_livestream_recording_not_available(self, initial_player_response):
        try:
            return initial_player_response['playabilityStatus']['reason'] == 'This live stream recording is not available.'
        except KeyError as e:
            if e.args[0] == 'reason':
                return False

    def video_is_unavailable(self, initial_player_response, initial_data):
        try:
            return 'contents' not in initial_data or initial_player_response['playabilityStatus']['reason'] == 'Video unavailable'
        except KeyError as e:
            if e.args[0] == 'reason':
                return False

    def video_like_count(self, initial_data):
        # Like count index is variable; we find it here before trying to access
        like_count_index = 0

        for item in initial_data['contents']['twoColumnWatchNextResults']['results']['results']['contents']:
            if 'videoPrimaryInfoRenderer' in item:
                break
            like_count_index += 1

        # Get like count
        like_text = initial_data['contents']['twoColumnWatchNextResults']['results']['results']['contents'][like_count_index]['videoPrimaryInfoRenderer']['videoActions']['menuRenderer']['topLevelButtons'][0]['toggleButtonRenderer']['accessibilityData']['accessibilityData']['label']
        
        if like_text == 'I like this':
            return None

        likes = int(like_text.split('with ')[1].split(' ')[0].replace(',', ''))
        return likes

    def video_title(self, initial_player_response):
        return initial_player_response['videoDetails']['title']

    def video_info(self, video_id, response):
        initial_player_response = self.js_var(response, 'ytInitialPlayerResponse')
        initial_data = self.js_var(response, 'ytInitialData')

        row = {}
        row['video_id'] = video_id

        if self.video_is_unavailable(initial_player_response, initial_data):
            row['unavailable'] = True
            return row

        if self.video_is_removed(initial_player_response):
            row['unavailable'] = True
            row['removed'] = True
            return row

        row['private'] = False
        row['requires_payment'] = False
        row['is_livestream_recording_not_available'] = False

        if self.video_is_playable(initial_player_response):

            if self.video_is_private(initial_player_response):
                row['private'] = True
                return row

            row['requires_payment'] = self.video_requires_payment(initial_player_response)
            row['livestream_recording_not_available'] = self.video_livestream_recording_not_available(initial_player_response)

        row['title'] = self.video_title(initial_player_response)
        row['description'] = initial_player_response['videoDetails']['shortDescription']
        row['view_count'] = int(initial_player_response['videoDetails']['viewCount'])
        row['like_count']= self.video_like_count(initial_data)
        row['length_seconds'] = int(initial_player_response['videoDetails']['lengthSeconds'])
        row['channel_name'] = initial_player_response['videoDetails']['author']
        row['channel_id'] = initial_player_response['videoDetails']['channelId']
        row['channel_url'] = initial_player_response['microformat']['playerMicroformatRenderer']['ownerProfileUrl']
        row['family_safe'] = initial_player_response['microformat']['playerMicroformatRenderer']['isFamilySafe']
        row['unlisted'] = initial_player_response['microformat']['playerMicroformatRenderer']['isUnlisted']
        row['live_content'] = initial_player_response['videoDetails']['isLiveContent']
        row['removed'] = False
        row['unavailable'] = False
        row['category'] = initial_player_response['microformat']['playerMicroformatRenderer']['category']
        row['upload_date'] = initial_player_response['microformat']['playerMicroformatRenderer']['uploadDate']
        row['publish_date'] = initial_player_response['microformat']['playerMicroformatRenderer']['publishDate']
        row['video_recommendations'] = self.video_recommendations(initial_data)
        
        return row

    async def video_metadata(self, video_ids):
        if self.proxy_url != None:
            session = aiohttp.ClientSession(connector=ProxyConnector.from_url(self.proxy_url))
        else:
            session = aiohttp.ClientSession()

        tasks = [self.get_video(session, video_id) for video_id in video_ids]
        responses = dict(await asyncio.gather(*tasks))

        await session.close()

        rows = [self.video_info(video_id, response) for video_id, response in responses.items()]
        return pd.DataFrame(rows).replace(r'^\s*$', None, regex=True)
