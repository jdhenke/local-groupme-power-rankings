# scrapes, analyzes and serves a webpage visualizing groupme power rankings
#
# it grabs the latest raw data from groupme and puts
# it reruns the analysis and stores the output in data.json
# it then serves a static http server of the local directory.
#
# no thought has been given to scale or security - this is for fun.

import numpy as np
import SimpleHTTPServer
import SocketServer
import codecs
import requests
import os
import json
import time
from pprint import pprint

# magic numbers; remove them if possible
PORT = 8000
REQUEST_WAIT = 5

# environment variablers
TOKEN = os.environ["GROUPME_TOKEN"]
GROUP_ID = os.environ["GROUPME_GROUP_ID"]

# TODO: impl rescraping for more likes

def main():
    scrape()
    analyze()
    # serve()

# ensures we have all the data from groupme
def scrape():
    # get latest group info
    group_url = "https://api.groupme.com/v3/groups/%s" % GROUP_ID
    params = {
        "token": TOKEN,
    }
    r = requests.get(group_url, params=params)
    if r.status_code != 200:
        raise Exception("Weird response in getting group info. %s" % r)
    with codecs.open("group.json", "w", "utf-8") as f:
        json.dump(json.loads(r.text)["response"], f)
    # get all messages
    messages_url = "https://api.groupme.com/v3/groups/%s/messages" % GROUP_ID
    if os.path.isfile("messages.json"):
        messages = json.load(open("messages.json"))
    else:
        messages = []
    print "Starting at %i messages." % len(messages)
    if len(messages) == 0:
        start_id = json.load(open("group.json"))["messages"]["last_message_id"]
    else:
        start_id = messages[-1]["id"]

    if len(set([m["id"] for m in messages])) != len(messages):
        raise Exception("Duplicate id detected in present messages.")

    # check before data I have
    while True:
        params = {
            "before_id": start_id,
            "limit": 100,
            "token": TOKEN,
        }
        r = requests.get(messages_url, params=params)
        if r.status_code == 304: break
        new_ms = json.loads(r.text)["response"]["messages"]
        messages += new_ms
        with open('messages.json', 'w') as f:
            json.dump(messages, f)
            f.close()
        start_id = new_ms[-1]["id"]
        print "Now at %i messages..." % len(messages)
        time.sleep(REQUEST_WAIT)

    # check after data I have
    end_id = messages[0]["id"]
    while True:
        params = {
            "after_id": end_id,
            "token": TOKEN,
            "limit": 100,
        }
        r = requests.get(messages_url, params=params)
        new_ms = json.loads(r.text)["response"]["messages"]
        if len(new_ms) == 0: break
        print "received %i messages" % len(new_ms)
        messages = new_ms[::-1] + messages
        if len(set([m["id"] for m in messages])) != len(messages):
            raise Exception("Duplicate id detected.")
        with open('messages.json', 'w') as f:
            json.dump(messages, f)
            f.close()
        end_id = messages[0]["id"]
        print "Now at %i messages..." % len(messages)
        time.sleep(REQUEST_WAIT)

# generates the info necessary for the UI from the raw-data
def analyze():
    group = json.load(open("group.json"))
    users = dict()
    for member in group["members"]:
        users[member["id"]] = member["nickname"]
    messages = json.load(open("messages.json"))
    counts = dict()

    for message in messages:
        user_id = message["user_id"]
        if user_id in ("system"): continue
        if user_id not in users:
            users[user_id] = message["name"]
        total, likes = counts.get(user_id, (0, 0))
        total += 1
        likes += len([1 for uid in message["favorited_by"] if uid != user_id])
        counts[user_id] = (total, likes)

    # get messages vs. likes
    counts_data = []
    for uid, (total, likes) in counts.iteritems():
        if total < 10: continue
        counts_data.append({
            "user_id": uid,
            "nickname": users[uid],
            "total": total,
            "likes": likes,
        })
    with open("counts.json", "w") as f:
        json.dump(counts_data, f)
    pprint(counts_data)

    for score, name in sorted([(1.0 * likes / total, users[uid]) for uid, (total, likes) in counts.iteritems() if total > 10]):
        print "%.3f" % score, name

# serves the UI
def serve():
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    httpd.serve_forever()

# kick things off when this script is run
if __name__ == '__main__':
    main()
