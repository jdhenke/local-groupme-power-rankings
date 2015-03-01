# performs eigenvector centrality analysis of a groupme convo, storing results
# in json files.
#
# be sure to set env. variables GROUPME_TOKEN andd GROUPME_GROUP_ID

import codecs, json, math, os, requests, time
import numpy as np
from scipy.sparse.linalg import eigs

# delay between requests to groupme api in seconds
REQUEST_WAIT = 1

# environment variables
TOKEN = os.environ["GROUPME_TOKEN"]
GROUP_ID = os.environ["GROUPME_GROUP_ID"]

# entry point
def main():
    group, messages = scrape()
    analyze(group, messages)

# scrape the latest data from groupme
def scrape():

    # get latest group info
    group = None
    group_url = "https://api.groupme.com/v3/groups/%s" % GROUP_ID
    params = {
        "token": TOKEN,
    }
    r = requests.get(group_url, params=params)
    if r.status_code != 200:
        raise Exception("Weird response in getting group info. %s" % r)
    with codecs.open("group.json", "w", "utf-8") as f:
        group = json.loads(r.text)["response"]
        json.dump(group, f)

    # get latest messages
    print "Scraping messages..."
    messages = []
    messages_url = "https://api.groupme.com/v3/groups/%s/messages" % GROUP_ID
    start_id = json.load(open("group.json"))["messages"]["last_message_id"]
    cutoff_time = time.mktime(time.gmtime()) - 2 * 7 * 24 * 60 * 60
    while True:
        params = {
            "before_id": start_id,
            "limit": 100,
            "token": TOKEN,
        }
        r = requests.get(messages_url, params=params)
        if r.status_code == 304: break
        new_ms = json.loads(r.text)["response"]["messages"]
        relevant_ms = [m for m in new_ms if m["created_at"] > cutoff_time]
        messages += relevant_ms
        print "\tNow at %i messages." % len(messages)
        if len(relevant_ms) < len(new_ms):
            break
        start_id = new_ms[-1]["id"]
        time.sleep(REQUEST_WAIT)

    with open('messages.json', 'w') as f:
        json.dump(messages, f)
        f.close()

    print "Done scraping. Retrieved %i messages." % len(messages)
    return group, messages

# generates the info necessary for the UI from the raw-data
def analyze(group, messages):

    print "Analyzing data..."

    ### aggregate data ###

    users = dict()  # users[user_id] = nickname
    counts = dict() # counts[u] = (messages, likes)
    pairs = dict()  # pairs[i][u] = n st. i liked ur message n times

    # get active members
    for member in group["members"]:
        users[member["user_id"]] = member["nickname"]

    for message in messages:

        # ignore messages from groupme itself
        if message["system"]: continue

        user_id = message["user_id"]

        # user may have left group but their messages still exist, so should
        # ensure we track nickname.
        if user_id not in users: users[user_id] = message["name"]

        # update data we're tracking, ignoring self likes
        total, likes = counts.get(user_id, (0, 0))
        total += 1
        likes += len([1 for uid in message["favorited_by"] if uid != user_id])
        counts[user_id] = (total, likes)
        for liker_id in message["favorited_by"]:
            if user_id == liker_id: continue
            pairs.setdefault(liker_id, dict())
            pairs[liker_id].setdefault(user_id, 0)
            pairs[liker_id][user_id] += 1

    ### store data and analysis in json files ###

    # filter to see if should include in analysis. math fails if a col of all 0s
    # exist, which is to say a person never liked any messages.
    #
    # TODO: optimize - the assume_included scheme is a hack for when a user has
    # some likes for users who themselves will not be included, thus resulting
    # in a column of zeros and bad times with the math.
    def include(u, assume_included=set()):
        if u in assume_included: return True
        ur_likes = pairs.get(u, dict()).iteritems()
        new_assume_included = assume_included.union({u})
        return sum([likes for (likee, likes) in ur_likes if likee != u and include(likee, new_assume_included)]) > 0

    # store messages vs. likes data
    counts_data = []
    for uid, (total, likes) in counts.iteritems():
        if not include(uid): continue
        counts_data.append({
            "user_id": uid,
            "nickname": users[uid],
            "total": total,
            "likes": likes,
        })
    with open("counts.json", "w") as f:
        json.dump(counts_data, f)

    # calculate power rankings
    users_list = [u for u in users.keys() if include(u)]
    n = len(users_list)
    A = np.zeros((n, n))
    for j, liker in enumerate(users_list):
        for i, likee in enumerate(users_list):
            if i == j: continue
            if liker in pairs and likee in pairs[liker]:
                A[i,j] += pairs[liker][likee]

    # normalize to a markov matrix
    M = A/A.sum(axis=0)
    # calculate k=1 eigenvectors of M with LargestMagintude
    vals, vecs = eigs(M, k=1, which='LM')
    # make vector explicitly real; all imaginary components should be 0
    R = vecs[:,0].real
    # normalize to be positive; |sum(R)| should be 1 already
    R /= R.sum()

    # store power ranking data
    power_ranking_data = []
    for i, user_id in enumerate(users_list):
        power_ranking_data.append({
            "user_id": user_id,
            "nickname": users[user_id],
            "power_ranking": R[i]
        })
    with open("power_ranking.json", "w") as f:
        json.dump(power_ranking_data, f)

    print "Done analyzing data."

# kick things off when this script is run
if __name__ == '__main__':
    main()
