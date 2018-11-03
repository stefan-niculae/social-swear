#!/usr/bin/env python

import sys, codecs, json, time
import numpy as np
import pandas as pd
#from TwitterApplicationHandler import TwitterApplicationHandler
from twython import TwythonStreamer, Twython
from datetime import datetime


SEARCHCOUNT = 100

class FilterAPI(TwythonStreamer):
	def on_success(self, data):  #KRC__this is the callback [event happens, this fires]
		dt = datetime.now()
		filename = "data/example_samp_-%s.txt" % (dt.strftime("%Y-%m-%d"),)  #KRC__store data in file, filename changes per day!
		#if 'text' in data:
		if data['text'].split()[0]=='RT':  #do not include retweets
			return

		print(data['text'])
		fp = codecs.open(filename, 'a', 'utf-8')
		fp.write(json.dumps(data))
		fp.write("\n")
		fp.close()

	def on_error(self, status_code, data):
		print("ERROR!")
		print(status_code)

class SampleAPI(TwythonStreamer):
	def on_success(self, data):  #KRC__this is the callback [event happens, this fires]

		#if the tweet is a 'non-oroginal' tweet..also, non-deleted tweet:
		if notOriginalTweet(data):
			return

		dt = datetime.now()
		filename = "data/example_sampFiltNew_again2_-%s.txt" % (dt.strftime("%Y-%m-%d"),)  #KRC__store data in file, filename changes per day!
		
		fp = codecs.open(filename, 'a', 'utf-8')
		fp.write(json.dumps(data))
		fp.write("\n")
		fp.close()

	def on_error(self, status_code, data):
		print("ERROR!")
		print(status_code)

def notOriginalTweet(tweet):
	if 'delete' in tweet:
		return True
	if 'retweeted_status' in tweet:
		return True
	if 'in_reply_to_status_id' in tweet:
		if tweet['in_reply_to_status_id']:
			return True
	if 'in_reply_to_status_id_str' in tweet:
		if tweet['in_reply_to_status_id_str']:
			return True
	if 'in_reply_to_user_id' in tweet:
		if tweet['in_reply_to_user_id']:
			return True
	if 'in_reply_to_user_id_str' in tweet:
		if tweet['in_reply_to_user_id_str']:
			return True
	if 'in_reply_to_screen_name' in tweet:
		if tweet['in_reply_to_screen_name']:
			return True
	return False
	#A BETTER WAY..have set(keys_to_check) then get tweet.keys() then check from there....

def printTweet(tweet):
	print(json.dumps(tweet,indent=2,sort_keys=False))
	return

#initializes the twython api object [opens the twitter api]
#returns the api object
def initAPI():
	# Load in OAuth Tokens  #KRC__these are specific to me! [twitter dev]
	app_key = "YOUR_API_KEY_HERE"  #KRC__api_key
	app_sec = "YOUR_API_SECRETKEY_HERE"  #KRC__api_secretKey
	user_key = "YOUR_ACCESS_TOKEN_HERE"  #KRC__access_token
	user_sec = "YOUR_ACCESS_TOKEN_SECRET_HERE"  #KRC__access_token_secret

	api = Twython(app_key, app_sec, user_key, user_sec)  #KRC__this is the connection!

	return api

def initStreamAPI(streamType='default'):
	# Load in OAuth Tokens  #KRC__these are specific to me! [twitter dev]
	app_key = "YOUR_API_KEY_HERE"  #KRC__api_key
	app_sec = "YOUR_API_SECRETKEY_HERE"  #KRC__api_secretKey
	user_key = "YOUR_ACCESS_TOKEN_HERE"  #KRC__access_token
	user_sec = "YOUR_ACCESS_TOKEN_SECRET_HERE"  #KRC__access_token_secret

	if streamType == 'sample':
		stream = SampleAPI(app_key, app_sec, user_key, user_sec)
		return stream

	stream = FilterAPI(app_key, app_sec, user_key, user_sec)  #KRC__this is the connection!

	return stream


#returns all results that were returned for the api call passed as func.
#returns list of objects [each entry was a return from the api]
#this helper function wraps rate limit checking around subsequent calls to avoid lockout/abusing rate limits
def rateLimitWrapper(api,func,kwargs,willingToWait=False,maxExecTime=10):
	#status = api.get_application_rate_limit_status()  #twitters rate limit status response..good for checking before start
	#numLeft = api.get_lastfunction_header('x-rate-limit-remaining')  #this is better b/c it does not make an extra api call just to get info
	#resetTime = api.get_lastfunction_header('x-rate-limit-reset')
	#func(args)
	print('entering rateLimitWrapper')
	results = []
	status = api.get_application_rate_limit_status()  #twitters rate limit status response..good for checking before start
	resetTime = int(status['resources']['search']['/search/tweets']['reset'])  #reset time
	remainingRequests = int(status['resources']['search']['/search/tweets']['remaining'])  #remaining calls available in this time windowq

	if remainingRequests == 0:  #already hit rate limit, either wait or return False
		if willingToWait == True:
			timeToWait = resetTime - time.time()
			time.sleep(timeToWait)
		else:
			print('You have hit rate limit and are not willing to wait. Canceling this call\n')
			return []

	#run first request here
	timeStart = time.time()
	response = func(**kwargs)
	results.append(response)
	print('1st response done')
	
	while ('next_results' in response['search_metadata'].keys()) and ((time.time() - timeStart) < maxExecTime):  #if a query returns empty status list, assume we are done. also done if time > maxExecTime
		#process previous request
		print('entering while loop')

		nextMax = int(response['search_metadata']['next_results'].split('=')[1].split('&')[0])  #we want tweets older than this one!
		kwargs['max_id'] = nextMax  #actually update the parameter

		resetTime = api.get_lastfunction_header('x-rate-limit-reset')
		remainingRequests = api.get_lastfunction_header('x-rate-limit-remaining')  #this is better b/c it does not make an extra api call just to get info
		
		if remainingRequests == 0:
			#need to wait
			print('waiting in while loop')
			timeToWait = resetTime - time.time()
			time.sleep(timeToWait)
		#make the request

		response = func(**kwargs)  #now include max_id
		results.append(response)
		
		print('while loop responce done')
	print('returning from rateLimitWrapper')
	return results

def rateLimitWrapperTimeline(api,func,kwargs,willingToWait=False,maxExecTime=10):
	#status = api.get_application_rate_limit_status()  #twitters rate limit status response..good for checking before start
	#numLeft = api.get_lastfunction_header('x-rate-limit-remaining')  #this is better b/c it does not make an extra api call just to get info
	#resetTime = api.get_lastfunction_header('x-rate-limit-reset')
	#func(args)
	#print('entering rateLimitWrapper')
	results = []
	status = api.get_application_rate_limit_status()  #twitters rate limit status response..good for checking before start
	resetTime = int(status['resources']['statuses']['/statuses/user_timeline']['reset'])  #reset time
	remainingRequests = int(status['resources']['statuses']['/statuses/user_timeline']['remaining'])  #remaining calls available in this time windowq

	#print('resetTime: %s'%resetTime)
	#print('remainingRequests: %s'%remainingRequests)

	if remainingRequests == 0:  #already hit rate limit, either wait or return False
		if willingToWait == True:
			timeToWait = resetTime - time.time()
			if timeToWait > 0:  #else, no wait needed
				print('rate limit, sleeping before while loop')
				time.sleep(timeToWait)
		else:
			print('You have hit rate limit and are not willing to wait. Canceling this call\n')
			return []

	#run first request here
	timeStart = time.time()
	try:
		response = func(**kwargs)
	except:
		print('ErrorCaught 1st')
		response = ['ErrorCaught']
		results.extend(response)
		return response

	if not response:  #i.e. the response was empty
		return []
	#results.append(response)
	results.extend(response)
	#print('1st response done')
	
	while ((time.time() - timeStart) < maxExecTime):  #if a query returns empty status list, assume we are done. also done if time > maxExecTime
		#process previous request
		#print('entering while loop')

		tweetIds = [status['id'] for status in response]
		nextMax = np.min(tweetIds)-1  #get the lowest id number for pagination next search
		##print('lowest_id: %s'%(nextMax+1))
		#print(kwargs)
		kwargs['max_id'] = int(nextMax)  #actually update the parameter


		resetTime = api.get_lastfunction_header('x-rate-limit-reset')
		remainingRequests = api.get_lastfunction_header('x-rate-limit-remaining')  #this is better b/c it does not make an extra api call just to get info
		
		if remainingRequests == 0:
			#need to wait
			#print('waiting in while loop')
			timeToWait = resetTime - time.time()
			if timeToWait > 0:  #else, we dont need to wait anymore
				print('rate limit, sleeping inside while loop')
				time.sleep(timeToWait)
		#make the request
		response = []  #reset
		try:
			response = func(**kwargs)  #now include max_id
		except:
			print('ErrorCaught in loop')
			response = ['ErrorCaught']
			results.extend(response)
			break
		##print('returned responses: %s'%len(response))
		if not response:  #i.e. the response was empty
			break
		#results.append(response)
		results.extend(response)
		
		#print('while loop responce done')
	print('returning from rateLimitWrapper')
	return results

def limits(api):
	return api.get_application_rate_limit_status()

def getTweetStats():
	print('NOT YET IMPLEMENTED...gwt likes, retweets, etc...other tweet metadata')


#input: none. hard coded the files that simple_top100_extract.script generated.
#output: top100_id_dictionary.json
def top100_raw_to_dict():
	#use ordered lists to get correct id's with correct names and usernames
	#final dict will be {id:[name,user_name]}
	#should have 100 entries
	ids = []
	with open('top100_ids_raw.txt','r') as f:
		for line in f:
			ids.append(int(line.split('"')[-2].replace('list-','')))
	if len(ids) != 100:
		print('Error extracting ids.\nids dump: \n%s'%ids)
		sys.exit()

	names = []
	with open('top100_name_raw.txt','r') as f:
		for line in f:
			names.append(line.split('"')[-2])
	if len(names) != 100:
		print('Error extracting ids.\nids dump: \n%s'%ids)
		sys.exit()

	usernames = []
	with open('top100_username_raw.txt','r') as f:
		for line in f:
			line = line.strip()
			if line.startswith('alt='):
				if line.startswith('alt="Friend or Follow"'):
					continue
				elif line.startswith('alt="verified"'):
					continue
				usernames.append(line.split('"')[-2])

	top100 = {}
	for i,uid in enumerate(ids):
		top100[uid] = [usernames[i],names[i]]

	jsonStr = json.dumps(top100)
	with open('top100_id_dictionary.json','w') as fn:
		fn.write(jsonStr)


#read in file filename [json encoded]
#return dict
def json_to_dict(filename):
	with open(filename,'r') as f:
		jstr = f.readlines()
	return json.loads(jstr[0])


###converting raw json twitter timeline data to dataframe
COLUMNS = ['tweet_id','date','user_id','text','text_noMentions','is_quote_status','is_reply_to_status','is_reply_to_user','numMentions',\
    'user_verified','user_description_text','user_followers_count','user_friends_count',\
    'user_listed_count','user_favourites_count','user_statuses_count','retweet_count','favorite_count']
COLUMNS_USER = ['user_id','user_verified','user_description_text','user_followers_count','user_friends_count',\
    'user_listed_count','user_favourites_count','user_statuses_count']

def handleMentions(tweet):
    numMentions = len(tweet['entities']['user_mentions'])
    if numMentions == 0:
        return numMentions,'NO_USER_MENTIONS'
    #else, strip the mentions!
    indexes = [mention['indices'] for mention in tweet['entities']['user_mentions']]
    indexes = np.flipud(indexes)  #remove from the back so indexes dont get messed up
    strippedText = tweet['text']
    for idx in indexes:
        strippedText = strippedText.replace(strippedText[idx[0]:idx[1]],'')
    strippedText = strippedText.strip()
    return numMentions,strippedText

def getReplyInfo(tweet):
    statusReply = False
    userReply = False
    if tweet['in_reply_to_status_id']:
        statusReply = True
    if tweet['in_reply_to_user_id']:
        userReply = True
    return statusReply,userReply

"""
Maps user timeline to DataFrame. Includes user metadata features and tweet features.

Args:
    uid: The user_id of the current user
    data: Dict with two keys. 'user_info' and 'user_timeline'

Returns:
    DataFrame with rows = single tweet instance. columns = features [combined user and tweet]
    columns = ['text','text_noMentions','is_quote_status','is_reply','numMentions',\
    'user_verified','user_description_text','user_followers_count','user_friends_count',\
    'user_listed_count','user_favourites_count','user_statuses_count','retweet_count','favorite_count']
    
    column info[type:[range]:info]:
    'text':str:string:the raw text of the tweet, unchanged
    'text_noMentions':str:string:the text of the tweet with @mentions removed [='NO_USER_MENTIONS if 0 mentions']
    'is_quote_status':bool:T/F:denotes if the tweet is a quote status of another tweet
    'is_reply_to_status':bool:T/F:denotes if the tweet is a reply to someone elses tweet
    'is_reply_to_user':bool:T/F:denotes if the tweet is a reply to a user
    'numMentions':int:int:number of mentions found in the tweet
    'user_verified':bool:T/F:denotes if the user is a verified user
    'user_description_text':str:string:raw text of the user's profile description
    'user_followers_count':int:int:number of followers the user has
    'user_friends_count':int:int:number of people the user follows
    'user_listed_count':int:int:number of lists the user is a part of
    'user_favourites_count':int:int:number of tweets the user has liked to date
    'user_statuses_count':int:int:number of tweets this user has authored to date [note that timeline acquisition is limited to 3200 latest tweets]
    'retweet_count':int:int:number of times this tweet has been retweeted [at time of collection]
    'favorite_count':int:int:number of times this tweet has been liked [at time of collection]
"""
def rawTimelineToTrainingInstances(uid,data):
    outData = pd.DataFrame(columns=COLUMNS)
    userData = pd.DataFrame(columns=COLUMNS_USER)
    userData = userData.append({'user_verified':data['user_info']['verified']},ignore_index=True)  #need to do for the first one...
    #userData['user_verified'] = data['user_info']['verified']
    userData['user_id'] = int(uid)
    userData['user_description_text'] = data['user_info']['description']
    userData['user_followers_count'] = data['user_info']['followers_count']
    userData['user_friends_count'] = data['user_info']['friends_count']
    userData['user_listed_count'] = data['user_info']['listed_count']
    userData['user_favourites_count'] = data['user_info']['favourites_count']
    userData['user_statuses_count'] = data['user_info']['statuses_count']
    #print(len(data['user_timeline']))
    #print(userData)
    for tweet in data['user_timeline']:
        if 'ErrorCaught' in tweet:
            print('Handled Tweet ErrorCaught')
            continue
        if 'delete' in tweet:
            print('Handled deleted tweet')
            continue
        tweetData = pd.DataFrame(columns=COLUMNS)  #this is a data instance
        tweetData = tweetData.append(userData,sort=False)  #user data is constant for a single call to this function
        tweetData['tweet_id'] = int(tweet['id'])
        tweetData['date'] = tweet['created_at']
        tweetData['text'] = tweet['text']
        numMentions,strippedText = handleMentions(tweet)
        tweetData['text_noMentions'] = strippedText
        tweetData['is_quote_status'] = tweet['is_quote_status']
        statusReply,userReply = getReplyInfo(tweet)
        tweetData['is_reply_to_status'] = statusReply
        tweetData['is_reply_to_user'] = userReply
        tweetData['numMentions'] = numMentions
        tweetData['retweet_count'] = tweet['retweet_count']
        tweetData['favorite_count'] = tweet['favorite_count']
        outData = outData.append(tweetData,sort=False)
        #print(tweetData)
    outData.set_index('user_id')
    outData = outData.infer_objects()
    return outData
