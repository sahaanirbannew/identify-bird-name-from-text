import pickle 
from Levenshtein import distance as levenshtein_distance
import re
import tweepy
import preprocessor as p
p.set_options(p.OPT.EMOJI, p.OPT.MENTION, p.OPT.URL, p.OPT.SMILEY, p.OPT.NUMBER, p.OPT.HASHTAG)
from ekphrasis.classes.segmenter import Segmenter
seg_tw = Segmenter(corpus="english")
import requests
from flask import Flask, request, render_template
ON_HEROKU = os.environ.get('ON_HEROKU')

spelling_corrections = {}
spelling_corrections["grey"] = "gray" 
spelling_corrections["pegion"] = "pigeon" 
spelling_corrections["brested"] = "breasted" 
spelling_corrections["serpant"] = "serpent" 
spelling_corrections["avedavat"] = "avadavat" 
spelling_corrections["open billed stork"] = "asian openbill" 
spelling_corrections["secretary bird"] = "Secretarybird" 
spelling_corrections["dollar bird"] = "dollarbird"
path = "" 

def get_eBird_commonNames_data(path):
  file = open(path+"bird_dict_comName",'rb')
  try:
    eBird_commonNames_data = pickle.load(file)
    return eBird_commonNames_data 
  except Exception as e:
    print(str(e))
    return 0
ebirds = get_eBird_commonNames_data(path)

def load_all_birds_list(path):
  file = open(path+"bird_list_df",'rb')
  bird_list_df = pickle.load(file)
  try: 
    return bird_list_df
  except:
    print("Error: No bird list found.")
    return 0
wikibirds = load_all_birds_list(path) 

def basic_preprocess(tweet, spelling_corrections):
  tweet = tweet.lower()
  tweet = p.clean(tweet)
  tweet = tweet.replace("\n"," ")  
  tweet = tweet.replace("\\n"," ") 
  if tweet[:2] == "b'": tweet = tweet[1:] 
  tweet = tweet.replace("'","")
  tweet = tweet.replace("#","")
  tweet = re.sub(r'[^\w\s]', ' ', tweet)
  tweet = re.sub(r' x..', '', tweet)
  tweet = re.sub(r' +', ' ', tweet) 
  tweet = tweet.replace("x9c","")
  tweet = tweet.strip()
  for key in spelling_corrections: 
    if tweet.find(key)>-1: 
      tweet = tweet.replace(key,spelling_corrections[key])
  return tweet 

def add_words_to_bird_vocab(bird_name, list_, spelling_corrections): 
  words = basic_preprocess(bird_name,spelling_corrections).split(" ")
  for word in words:
    if word not in list_:
      list_.append(word)
  return list_

def add_birdnames_to_list(bird_name, list_, spelling_corrections): 
  bird_name__ = basic_preprocess(bird_name, spelling_corrections) 
  if bird_name__ not in list_: 
    list_.append(bird_name__) 
  return list_

all_birds_list = [] 
birdnames_words = [] 
birdnames = wikibirds["bird_name"].unique().tolist() 
for speciesTag in ebirds:
  all_birds_list = add_birdnames_to_list(ebirds[speciesTag], all_birds_list, spelling_corrections)
  birdnames_words = add_words_to_bird_vocab(ebirds[speciesTag], birdnames_words, spelling_corrections) 
for birdname in birdnames: 
  all_birds_list = add_birdnames_to_list(birdname, all_birds_list, spelling_corrections)
  birdnames_words = add_words_to_bird_vocab(birdname, birdnames_words, spelling_corrections) 

def return_alt_word(word_,birdnames_words): 
  min_distance = 1000
  if word_ not in birdnames_words: 
    for word in birdnames_words: 
      dist_ = levenshtein_distance(word_,word)
      if dist_ < min_distance: 
        min_distance = dist_
        word__ = word 
  else: 
    return word_  
  return word__

def return_alt_bird(word_,all_birds_list): 
  min_distance = 1000
  if word_ not in all_birds_list: 
    for word in all_birds_list: 
      dist_ = levenshtein_distance(word_,word)
      if dist_ < min_distance: 
        min_distance = dist_
        word__ = word 
  else: 
    return word_  
  return word__

def try_removing_hashtags(text,all_birds_list,birdnames_words):
  status = False 
  #print(text)
  hashtags = re.findall(r"#(\w+)", text) 
  for hashtag in hashtags:
    segmented_ = seg_tw.segment(hashtag) 
    words = segmented_.split(" ")
    for word in words: #in case there is a spelling mistake. #works only when there is a spelling mistake
      segmented_ = segmented_.replace(word, return_alt_word(word,birdnames_words))
    for bird in all_birds_list: #not an exact match, because people always do not write the full name.
      if bird.find(segmented_) > -1: 
        text = text.replace("#"+hashtag,segmented_)
        status = True
  return text

def get_bird_names(tweet, birdnames_words):
  api_url = "https://bird-name-ner-nlp.herokuapp.com/ner?sent="+tweet
  response = requests.get(api_url).json() 
  bird_list_= [] 
  for bird in response['bird-wiki']: 
    if bird not in bird_list_: 
      bird_list_.append(bird) 
  for bird in response['bird-ebird']: 
    if bird not in bird_list_: 
      bird_list_.append(bird) 
  
  for bird in response['bird-ner']:
    status_ = False 
    if bird not in bird_list_: 
      #check for spelling errors.
      for word in bird.split(" "):
        bird = bird.replace(word, return_alt_word(word,birdnames_words)) 

      if len(bird)>0:
        for bird_ in bird_list_:
          if bird_.find(bird) > -1: #if it is found, then no action.  
            status_ = True #found 
            break
        if status_ == False:
          bird_list_.append(bird) 
  
  return bird_list_

def get_birds_given_text(tweet,all_birds_list, birdnames_words,spelling_corrections):
  tweet = try_removing_hashtags(tweet,all_birds_list, birdnames_words) 
  tweet = basic_preprocess(tweet, spelling_corrections)  
  bird_list = get_bird_names(tweet, birdnames_words) 
  return bird_list 


@app.route('/bird') 
def send_birdname():
  tweet = request.args.get('sent')
  bird_list = get_birds_given_text(tweet,all_birds_list, birdnames_words, spelling_corrections)
  return bird_list
  
