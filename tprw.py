import browser_cookie3
import bs4
import grequests
import json
import os
import queue
import re
import requests
import sys
import tempfile
import threading
import webbrowser
import unicodedata

### SETTINGS ###
load_from_file = True
################

def get_replays(results, replay_type):
    url = 'http://tools.torebaprizewatcher.com/serverside/model.php'
    headers = {
        'Pragma': 'no-cache',
        'DNT': '1',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Referer': 'http://tools.torebaprizewatcher.com/replay.html',
    }
    params = (
        ('q', 'get_top_items'),
        ('filter', replay_type),
    )
    added_prize_ids = []
    prizes = []
    data = '[]'

    # keep retrieving until there is data
    while data == '[]':
        response = requests.get(url, headers=headers, params=params)
        data = response.text
        if data == '[]':
            print('Empty result returned, retrying')

    # data finally loaded, time to parse it for searching
    data = json.loads(data)['data']
    for item in data:
        prize_id = item['id']
        prize_name = item['item_name']
        if not prize_id in added_prize_ids:
            added_prize_ids.append(prize_id)
            prizes.append({'id': prize_id, 'name': prize_name})
    results.put(prizes)
    
    # save the data
    with open('torebadata_' + replay_type, 'w+') as f:
        f.write(response.text)
    print('torebadata_' + replay_type + ' writen!')


def get_links(prize_id, prize_name):
    url = 'http://tools.torebaprizewatcher.com/serverside/get_prize_detail.php'
    headers = {
        'Pragma': 'no-cache',
        'DNT': '1',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Referer': 'http://tools.torebaprizewatcher.com/prize.html',
    }
    params = (
        ('item', prize_id),
    )
    data = '[]'
    response = requests.get(url, headers=headers, params=params)
    data = response.text
    data = json.loads(data)

    if 'data' in data:
        toreba_urls = []
        data = data['data']
        cookies = browser_cookie3.chrome()
        for item in data:
            headers = {
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36',
                'DNT': '1',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
                'Referer': item['replay_url']
            }
            toreba_urls.append(grequests.get(item['replay_url'], headers=headers, cookies=cookies))
        responses = grequests.map(toreba_urls)

        # build html response
        html_response = '<h1 style="text-align:center;">{}: {}</h1>'.format(prize_id, prize_name)
        html_response += '<div style="display:flex;flex-wrap:wrap;justify-content:center;">'
        for i, response in enumerate(responses):
            html = bs4.BeautifulSoup(response.text, 'html.parser')
            video_elem = html.select_one('video source')
            video_date = html.select_one('.uploadtime_replay.p8')
            # extract the time only, remove other characters
            video_date = re.sub('[^0-9\-\: ]', '', video_date.text)

            html_response += '<div style="margin:30px;display:flex;flex-direction:row;">'
            html_response += '<div>'
            html_response += '<div style="font-size:36px;margin-right:10px;">{}</div>'.format(i + 1)
            html_response += '<div style="font-size:12px;margin-right:10px;">{}</div>'.format(video_date)
            html_response += '</div>'
            html_response += '<video preload="auto" src="{}" controls></video>'.format(video_elem['src'])
            html_response += '</div>'
        html_response += '</div>'
        return html_response
    else:
        print('No replays for {}-{}'.format(prize_id, prize_name))
        return ''


def print_list(prizes):
    prize_list = ''
    for prize in prizes:
        prize_list += ('{}: {}\n'.format(prize['id'], prize['name']))
    print(prize_list)

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '-f':
        load_from_file = False
    results = queue.Queue()
    print('Retrieving all records')
    prizes = []
    added_prize_ids = []
    if load_from_file:
        for replay_type in ('1', '7', 'hot'):
            filepath = 'torebadata_' + replay_type
            if not os.path.exists(filepath):
                continue
            print(filepath + ' found, loading from file')
            file = open(filepath, 'r')
            data = file.read()
            data = json.loads(data)['data']
            for item in data:
                prize_id = item['id']
                prize_name = item['item_name']
                if not prize_id in added_prize_ids:
                    added_prize_ids.append(prize_id)
                    prizes.append({'id': prize_id, 'name': prize_name})
            file.close()
    else:
        threads = []
        threads.append(threading.Thread(target=get_replays, args=(results, 'hot')))
        threads.append(threading.Thread(target=get_replays, args=(results, '1')))
        threads.append(threading.Thread(target=get_replays, args=(results, '7')))
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        print('Records retrieved!')
        while not results.empty():
            thread_prizes = results.get()
            for prize in thread_prizes:
                if not prize['id'] in added_prize_ids:
                    added_prize_ids.append(prize['id'])
                    prizes.append(prize)

    id_regex = r'(\d{5})+'
    while True:
        user_input = input('default search | <id/list of ids> to show replays | q to quit: ')
        if re.match(id_regex, user_input, re.IGNORECASE): # list of ids
            user_input = user_input.split(' ')

            # open tmp file for writing
            tmp_file = open('tmp.html', 'w')
            tmp_file.write('<html>')
            
            for prize in prizes:
                if prize['id'] in user_input:
                    data = get_links(prize['id'], prize['name'])
                    tmp_file.write(data)

            # finish writing data to tmp file
            tmp_file.write('</html>')
            tmp_file.close()
            # open tmp file in webbrowser
            webbrowser.open_new_tab('tmp.html')
                    
        elif user_input == 'q':
            # quit program
            break
        else:
            # default search
            filtered = []
            # all search terms must match, IMPLICIT AND style
            # e.g. If the prize name is 'Sumikkogurashi mug cup'
            # input = ['Summikogurashi', 'mug', 'cup'], match passes
            # input = ['Summikogurashi', 'mug', 'cup2'], match will fail
            user_input = user_input.split(' ')
            for prize in prizes:
                is_all_match = True
                for user_input_item in user_input:
                    if not re.match('.*' + user_input_item + '.*', prize['name'], re.IGNORECASE):
                        is_all_match = False
                        break
                if is_all_match:
                    filtered.append(prize)

            # pretty format to console
            for item in filtered:
                print('{: >5}: {}'.format(item['id'], item['name']))
        
