from __future__ import print_function
import json
import os
import time
from slackclient import SlackClient
from pprint import pprint
import mmap
import string
import re

import config

config.setup_examples()
import infermedica_api

class QCareApp:
  uus = ""
  oirereet = ""
  def __init__(self, bot_id, 
               slack_client, conversation_client):
    self.bot_id = bot_id
	

    self.slack_client = slack_client
    self.conversation_client = conversation_client

    
    self.at_bot = "<@" + bot_id + ">"
    self.delay = 0.5 #second
    self.workspace_id = '9afdcff6-aef5-4e5c-8022-43121dd5b22f'
    self.context = {}
    self.api = infermedica_api.get_api()

  def parse_slack_output(self, slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
      for output in output_list:
        if output and 'text' in output and \
          'user_profile' not in output and \
          self.at_bot in output['text']:
          return output['text'].split(self.at_bot)[1].strip().lower(), \
                 output['channel']
    return None, None

  def get_diagnosis(self, symptoms):
    api = infermedica_api.get_api()
    tyyppi= infermedica_api.Diagnosis(sex='female', age=35)
    symp_idit = open('symptoms_ids.txt', 'r')
    c = 'c_'
    for oire in symp_idit:
      tyyppi.add_symptom('s_'+oire, 'present')
    tyyppi = api.diagnosis(tyyppi)
    tyyppi2 = str(tyyppi)
    diagsiisti= open('diag_siisti.txt','w')
    with open('siisti_sairaudet.txt', 'w') as si:
      si.writelines(tyyppi2)
    with open('siisti_sairaudet.txt', 'rt') as sii:
      for i in sii:
        i = str(i)
        for n in re.findall(c, i):
          seuraava = str(next(sii))
          id_siivo = seuraava.split(':')[1]
          id_melkein = id_siivo.split('"')[1]
          id_siivottu = id_melkein.split('"')[0]
          diagsiisti.write(id_siivottu)
    diagsiisti.close()
    diagsiisti= open('diag_siisti.txt','r')
    diagnoosit = ""
    for sairaus in diagsiisti:
      diagnoosit = diagnoosit+sairaus+"\n"
    diagsiisti.close()
    return str(diagnoosit)
	
  def post_to_slack(self, response, channel):   
    self.slack_client.api_call("chat.postMessage", 
                          channel=channel,
                          text=response, as_user=True)

  def handle_symptoms_message(self, message):
    api = infermedica_api.get_api()
    response = api.parse(message)
    self.get_symptoms_id(str(response))
    return str(response)


  def get_symptoms_id(self, symptoms):
    symptoms_ids_auki = open('symptoms_ids.txt','w')
    symptoms = str(symptoms)
    self.oirereet = symptoms
    assa = 's_'
    with open('symp_mentions.txt', 'w') as ff:
      ff.writelines(symptoms)
    with open('symp_mentions.txt', 'rt') as f:
      for inne in f:
        inne = str(inne)
        for m in re.findall(assa, inne):
          id_siivo = inne.split('_')[1]
          id_siivottu = id_siivo.split('"')[0]
          symptoms_ids_auki.write(id_siivottu)
    symptoms_ids_auki.close()

  def handle_message(self, message, channel):
    watson_response = self.conversation_client.message(
      workspace_id=self.workspace_id, 
      message_input={'text': message},
      context=self.context)
	  
    self.context = watson_response['context']

    if watson_response['entities'] and \
         watson_response['entities'][0]['entity'] == 'symptoms':
      symptoms = watson_response['entities'][0]['value']
      response = "Here's a list of your symptoms " +self.handle_symptoms_message(symptoms) +"\n"+ "The most possible diagnosis could be " + self.get_diagnosis(symptoms)
    else:
      response ="sry try again "
      for text in watson_response['output']['text']:
        response += text + "\n"

    self.post_to_slack(response, channel)

  def run(self):
    if self.slack_client.rtm_connect():
	
      print("QCARE RUNNING ")
      while True:
	  
	  
        slack_output = self.slack_client.rtm_read()
        message, channel = self.parse_slack_output(slack_output)
        if message and channel:
          self.handle_message(message, channel)
        time.sleep(self.delay)
    else:
      print("Connection failed. Invalid Slack token or bot ID?")
