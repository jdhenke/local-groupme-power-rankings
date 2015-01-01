# scrapes, analyzes and serves a webpage visualizing groupme power rankings
#
# it grabs the latest raw data from groupme and puts
# it reruns the analysis and stores the output in data.json
# it then serves a static http server of the local directory.
#
# no thought has been given to scale or security - this is for fun.

import numpy as np
import codecs
import requests
import os
import json
import time
from pprint import pprint
import math

# magic numbers; remove them if possible
REQUEST_WAIT = 1
REFRESH_WINDOW = 7 * 60 * 60 * 24 # number of seconds in a week

# environment variables
TOKEN = os.environ["GROUPME_TOKEN"]
GROUP_ID = os.environ["GROUPME_GROUP_ID"]

def main():
    scrape()
    analyze()

# ensures we have all the raw data from groupme
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

    # scrape all messages, building off the current cache if it exists and
    # refreshing recent messages to account for more likes
    messages_url = "https://api.groupme.com/v3/groups/%s/messages" % GROUP_ID
    if os.path.isfile("messages.json"):
        messages = json.load(open("messages.json"))
        print "Loaded %i messages from cache." % len(messages)
    else:
        messages = []

    if len(messages) == 0:
        print "No cached messages found."
        print "Working backwards to retrieve all messages..."
        start_id = json.load(open("group.json"))["messages"]["last_message_id"]
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
            print "\tNow at %i messages." % len(messages)
            time.sleep(REQUEST_WAIT)
        print "Done retrieving all messages."

    if len(set([m["id"] for m in messages])) != len(messages):
        raise Exception("Duplicate message id detected.")

    i = 0
    refresh_time = messages[0]["created_at"] - REFRESH_WINDOW
    while i < len(messages) and messages[i]["created_at"] > refresh_time:
        i += 1
    end_id = messages[i]["id"]
    messages = messages[i:]
    print "Refreshing last %i messages..." % i
    while True:
        params = {
            "after_id": end_id,
            "token": TOKEN,
            "limit": 100,
        }
        r = requests.get(messages_url, params=params)
        new_ms = json.loads(r.text)["response"]["messages"]
        if len(new_ms) == 0: break
        messages = new_ms[::-1] + messages
        if len(set([m["id"] for m in messages])) != len(messages):
            raise Exception("Duplicate message id detected.")
        with open('messages.json', 'w') as f:
            json.dump(messages, f)
            f.close()
        end_id = messages[0]["id"]
        print "Now at %i messages..." % len(messages)
        time.sleep(REQUEST_WAIT)

    print "Scraping finished with %i messages in cache." % len(messages)

# generates the info necessary for the UI from the raw-data
def analyze():

    group = json.load(open("group.json"))
    users = dict()
    for member in group["members"]:
        users[member["user_id"]] = member["nickname"]
    messages = json.load(open("messages.json"))
    counts = dict()
    tf = dict() # tf[user_id][term] = count
    pairs = dict() # pairs[i][u] = n := i liked ur message n times

    for message in messages:
        user_id = message["user_id"]
        if user_id in ("system"): continue
        if user_id not in users:
            users[user_id] = message["name"]
        if user_id not in tf: tf[user_id] = dict()
        total, likes = counts.get(user_id, (0, 0))
        total += 1
        likes += len([1 for uid in message["favorited_by"] if uid != user_id])
        for liker_id in message["favorited_by"]:
            pairs.setdefault(liker_id, dict())
            pairs[liker_id].setdefault(user_id, 0)
            pairs[liker_id][user_id] += 1
        counts[user_id] = (total, likes)


        if message["text"] is not None:
            for term in message["text"].lower().replace(".","").replace("'","").replace(",","").replace('"', '').replace("-", "").replace("=", "").split(" "):
                term = term.strip()
                if len(term) == 0: continue
                count = tf[user_id].get(term, 0)
                tf[user_id][term] = count + 1

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

    # calculate power rankings
    users_list = [u for u in users.keys() if counts[u][0] > 10]
    n = len(users_list)
    A = np.zeros((n, n))
    for i, liker in enumerate(users_list):
        for j, likee in enumerate(users_list):
            if i == j: continue
            if liker in pairs and likee in pairs[liker]:
                A[i,j] += pairs[liker][likee]
    M = A/A.sum(axis=0)
    R = np.linalg.inv(np.eye(n) - M).dot(np.ones(n))
    R /= sum(R)
    power_ranking_data = []
    for i, user_id in enumerate(users_list):
        power_ranking_data.append({
            "user_id": user_id,
            "nickname": users[user_id],
            "power_ranking": R[i]
        })
    with open("power_ranking.json", "w") as f:
        json.dump(power_ranking_data, f)

# kick things off when this script is run
if __name__ == '__main__':
    main()
