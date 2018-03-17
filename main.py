#!/usr/bin/python3

import praw
import os
import logging.handlers
import time
import sys
import requests
from datetime import datetime
import collections
import traceback

### Config ###
LOG_FOLDER_NAME = "logs"
SUBREDDIT = "thepewdiepie"
USER_AGENT = "thepewdiepie flair updater (by /u/Watchful1)"

### Logging setup ###
LOG_LEVEL = logging.DEBUG
if not os.path.exists(LOG_FOLDER_NAME):
    os.makedirs(LOG_FOLDER_NAME)
LOG_FILENAME = LOG_FOLDER_NAME+"/"+"bot.log"
LOG_FILE_BACKUPCOUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256 * 16

log = logging.getLogger("bot")
log.setLevel(LOG_LEVEL)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
log_stderrHandler = logging.StreamHandler()
log_stderrHandler.setFormatter(log_formatter)
log.addHandler(log_stderrHandler)
if LOG_FILENAME is not None:
	log_fileHandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_MAXSIZE, backupCount=LOG_FILE_BACKUPCOUNT)
	log_formatter_file = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	log_fileHandler.setFormatter(log_formatter_file)
	log.addHandler(log_fileHandler)

log.debug("Connecting to reddit")

username = "USERNAME"
password = "PASSWORD"
client_id = "CLIENT_ID"
client_secret = "CLIENT_SECRET"

debug = False
if len(sys.argv) >= 1:
	for arg in sys.argv:
		if arg == 'debug':
			debug = True
else:
	log.error("No user specified, aborting")
	sys.exit(0)

try:
	r = praw.Reddit(username=username,
					password=password,
					client_id=client_id,
					client_secret=client_secret,
					user_agent=USER_AGENT)
except Exception as err:
	log.error("Could not log into reddit with username /u/{}".format(username))
	sys.exit(0)

log.info("Logged into reddit as /u/{}".format(str(r.user.me())))

artDomains = {'gyazo.com', 'i.reddituploads.com', 'instagram.com', 'i.imgur.com', 'imgur.com', 'i.redd.it'}
videoDomains = {'v.redd.it', 'youtu.be', 'youtube.com'}

url = "https://api.pushshift.io/reddit/submission/search?limit=1000&sort=desc&subreddit={}&before=".format(SUBREDDIT)
previousTime = int(time.mktime(datetime.utcnow().timetuple()))
count = 0
flairs = collections.defaultdict(int)
postIds = []
while True:
	newUrl = url+str(previousTime)
	json = requests.get(newUrl, headers={'User-Agent': USER_AGENT})
	posts = json.json()['data']
	if len(posts) == 0:
		break

	for post in posts:
		previousTime = post['created_utc'] - 1
		count += 1
		postIds.append(post['id'])
		if count > 10:
			break

	if count > 10:
		break

log.info("Found {} posts".format(count))

flairsUpdated = 0
errors = 0
for i, postId in enumerate(postIds):
	newFlair = None
	reason = "No change"

	try:
		submission = r.submission(id=postId)

		if submission.is_self:
			if submission.link_flair_text is None:
				# this is a self post without a flair, give it the Discussion flair
				newFlair = 'Discussion'
				reason = "Self post without a flair, setting Discussion"

		else:
			if submission.link_flair_text is not None:
				if submission.link_flair_text == 'FanArt':
					# this is link post with the FanArt flair, change it to FanArt/Meme
					newFlair = 'FanArt/Meme'
					reason = "Link post with the FanArt flair, changing to FanArt/Meme"

			else:
				if submission.domain in artDomains:
					# this is link post without a flair that is an art domain, set the flair to FanArt/Meme
					newFlair = 'FanArt/Meme'
					reason = "Link post without a flair with domain {}, setting FanArt/Meme".format(submission.domain)

				elif submission.domain in videoDomains:
					# this is link post without a flair that is an video domain, set the flair to Video
					newFlair = 'Video'
					reason = "Link post without a flair with domain {}, setting Video".format(submission.domain)

		submissionCreated = datetime.utcfromtimestamp(submission.created_utc)
		if newFlair is not None:
			flairsUpdated += 1
			submission.mod.flair(text=newFlair)
		log.info("{}/{}: {}: {}: {}".format(i + 1, count, submission.id, submissionCreated.strftime('%m/%d/%y'), reason))

	except Exception as err:
		log.warning("{}/{}: {}: {}: {}".format(i, count, postId, "--/--/--", "Something went wrong"))
		if debug:
			log.warning(traceback.format_exc())
		errors += 1

log.info("Updated flairs on {} of {} posts. Something went wrong with {} posts.".format(flairsUpdated, count, errors))
