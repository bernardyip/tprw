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
    while data == '[]':
        response = requests.get(url, headers=headers, params=params)
        data = response.text
        if data == '[]':
            print('Empty result returned, retrying')
    data = json.loads(data)['data']
    for item in data:
        prize_id = item['id']
        prize_name = item['item_name']
        if not prize_id in added_prize_ids:
            added_prize_ids.append(prize_id)
            prizes.append({'id': prize_id, 'name': prize_name})
    results.put(prizes)
    #Save the data
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
        
        with open('tmp.html', 'w') as tmp:
            tmp.write('<html><h1 style="text-align:center;">{}: {}</h1>'.format(prize_id, prize_name))
            i = 1
            for response in responses:
                html = bs4.BeautifulSoup(response.text, 'html.parser')
                video_elem = html.select('.factors_replay video source')
                tmp.write('<div style="display:flex; justify-content:center ;margin-bottom:30px;">')
                tmp.write('<div style="font-size:36px; margin-right:10px;">{}</div>'.format(i))
                tmp.write('<video preload="auto" src="{}" controls></video>'.format(video_elem[0]['src']))
                tmp.write('</div>')
                i += 1
            tmp.write('</html>')
        webbrowser.open_new_tab('tmp.html')
    else:
        print('No replays')
    

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

    #print_list(prizes)

    while True:
        user_input = input('default search | <id> to show replays | q to quit: ')
        if user_input.isdigit() and len(user_input) <= 5:  # id should be less than 5 digits
            for prize in prizes:
                if prize['id'] == user_input:
                    get_links(user_input, prize['name'])
        elif user_input == 'q':  # quit program
            try:
                os.remove('tmp.html')
            except:
                pass
            break
        else:  #default search
            filtered = []
            for prize in prizes:
                if re.match('.*' + user_input + '.*', prize['name'], re.IGNORECASE):
                    filtered.append(prize)
            for item in filtered:
                print('{: >5}: {}'.format(item['id'], item['name']))
        
