#!/usr/bin/env python

import sys, codecs, json, time
import numpy as np
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
	app_key = "DXuA9J6KSS8TWEelnR1TXxdY2"  #KRC__api_key
	app_sec = "QTjVQGET9JGLfbCWfWaJS8trxblFJiGA76Om2pPd4F9VNQweI4"  #KRC__api_secretKey
	user_key = "1035550749738987520-ugjvRAooLEiU2foekW7N1fNSHGcpeo"  #KRC__access_token
	user_sec = "x1tuHA0Pskq95WeQ0vbwIlCCMzVq9geDFewMfep28OaPi"  #KRC__access_token_secret

	api = Twython(app_key, app_sec, user_key, user_sec)  #KRC__this is the connection!

	return api

def initStreamAPI(streamType='default'):
	# Load in OAuth Tokens  #KRC__these are specific to me! [twitter dev]
	app_key = "DXuA9J6KSS8TWEelnR1TXxdY2"  #KRC__api_key
	app_sec = "QTjVQGET9JGLfbCWfWaJS8trxblFJiGA76Om2pPd4F9VNQweI4"  #KRC__api_secretKey
	user_key = "1035550749738987520-ugjvRAooLEiU2foekW7N1fNSHGcpeo"  #KRC__access_token
	user_sec = "x1tuHA0Pskq95WeQ0vbwIlCCMzVq9geDFewMfep28OaPi"  #KRC__access_token_secret

	if streamType == 'sample':
		stream = SampleAPI(app_key, app_sec, user_key, user_sec)
		return stream

	stream = FilterAPI(app_key, app_sec, user_key, user_sec)  #KRC__this is the connection!

	return stream

def simple(a,b,c):
	print('a: %s'%a)
	print('b: %s'%b)
	print('c: %s'%c)

def wrapper(func,kwargs):
	result = func(**kwargs)
	return result


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
