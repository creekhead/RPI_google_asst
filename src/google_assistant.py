#!/usr/bin/env python

# The code is based on google-assistant-sdk's hotword.py
# LED light is added to notify its status.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import print_function

import argparse
import os.path
import json
import subprocess
import time
import re
from random import *

from aiy.voice import tts
import aiy._drivers._player
import aiy._drivers._recorder
import aiy.i18n

import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.library import Assistant
from google.assistant.library.event import EventType
from google.assistant.library.file_helpers import existing_file

from pixels import pixels

DEVICE_API_URL = 'https://embeddedassistant.googleapis.com/v1alpha2'


def process_device_actions(event, device_id):
    if 'inputs' in event.args:
        for i in event.args['inputs']:
            if i['intent'] == 'action.devices.EXECUTE':
                for c in i['payload']['commands']:
                    for device in c['devices']:
                        if device['id'] == device_id:
                            if 'execution' in c:
                                for e in c['execution']:
                                    if 'params' in e:
                                        yield e['command'], e['params']
                                    else:
                                        yield e['command'], None


def say(words, lang=None, volume=60, pitch=130):
    """Says the given words in the given language with Google TTS engine.

    If lang is specified, e.g. "en-US", it will be used to say the given words.
    Otherwise, the language from aiy.i18n will be used.
    volume (optional) volume used to say the given words.
    pitch (optional) pitch to say the given words.
    Example: aiy.audio.say('This is an example', lang="en-US", volume=75, pitch=135)
    Any of the optional variables can be left out.
    """
    print("Say: ",words)
    if not lang:
        lang = aiy.i18n.get_language_code()
    tts.say(words, lang=lang, volume=volume, pitch=pitch)

def process_event(event, device_id, assistant_obj):
    """Pretty prints events.

    Prints all events that occur with two spaces between each new
    conversation and a single space between turns of a conversation.


    Args:
        event(event.Event): The current event to process.
        device_id(str): The device ID of the new instance.
    """

    print("DEBUG:")
    print(event)
    print()

    if event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        pixels.wakeup()

    if event.type == EventType.ON_END_OF_UTTERANCE:
        pixels.think()

    if event.type == EventType.ON_RESPONDING_STARTED:
        pixels.speak()

    if event.type == EventType.ON_RENDER_RESPONSE:
        pixels.think()
        speech_text = event.args["text"]

    if event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED:
        print("Detect ON_RECOGNIZING_SPEECH_FINISHED")

        text = event.args['text'].lower()
        print('You said:', text)

        if "turn" in text and "tv" in text:
            print("TURN TV DETECTED: ")
            if "off" in text:
                print("OFF")
            elif "on" in text:
                print("ON")

        #Set volume to X
        if "set" in text and "volume" in text:
            volume=get_trailing_number(text)
            print("SET VOLUME: ",volume)
            if "down" in text:
                print("DOWN")
                say_ok()
                for x in range(volume):
                    subprocess.call("irsend SEND_ONCE LGTV VOL_DOWN", shell=True)
                    time.sleep(1)

            elif "up" in text:
                print("UP")
                say_ok()
                for x in range(volume):
                    subprocess.call("irsend SEND_ONCE LGTV VOL_UP", shell=True)
                    time.sleep(1)


        if text == 'turn on the tv' or text == 'turn on tv':
            print("TURN ON THE TV HERE")
            assistant_obj.stop_conversation()
            say_ok()
            subprocess.call("irsend SEND_ONCE LGTV OFF", shell=True)
        elif text == 'turn off the tv' or text == 'turn off tv':
            print("TURN OFF THE TV HERE")
            assistant_obj.stop_conversation()
            say_ok()
            subprocess.call("irsend SEND_ONCE LGTV OFF", shell=True)
        elif ("set" in text or "turn" in text) and "sleep" in text:
            hours=get_trailing_number(text)
            print("TURN SLEEP ON HOURS:",hours)
            assistant_obj.stop_conversation()
            say_ok()
            subprocess.call("/home/pi/ir/sleep_tv.sh", shell=True)

        pixels.off()
    if event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT:
        print("Detect ON_CONVERSATION_TURN_TIMEOUT")
        pixels.off()

    if event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
        print("Detect ON_CONVERSATION_TURN_FINISHED")
        pixels.off()
        #RERUN AS IF THE with_follow_on_turn=true
        #pixels.listen()
        #assistant_obj.start_conversation()

        #if event.args and event.args['with_follow_on_turn']:
        #    pixels.listen()
        #else:
        #    pixels.off()
        #    print()

    if event.type == EventType.ON_DEVICE_ACTION:
        #pixels.off()
        print()

        for command, params in process_device_actions(event, device_id):
            print('Do command', command, 'with params', str(params))

            #CHECK ON/OFF LIGHTS
            if command=='action.devices.commands.Dock':
                bashCommand = "irsend SEND_ONCE LGTV OFF"
                process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
                output, error = process.communicate()

            if command=='action.devices.commands.OnOff':
                on=params.get("on", "False")

                if on==True:
                    print("OnOFF - ON Bed")
                    subprocess.call("irsend SEND_ONCE BED BACK_ON", shell=True)
                    time.sleep(1)
                    subprocess.call("irsend SEND_ONCE BED LEGS_ON", shell=True)

                if on==False:
                    print("OnOFF - OFF Bed")
                    subprocess.call("irsend SEND_ONCE BED ALL_OFF", shell=True)

            #check if its a START LIGHT Command - Sleep
            if command=='action.devices.commands.StartStop':
                start=params.get("start", "False")
                if start==False:
                    #STOP LIGHTS
                    print("Start SLEEP - ON")
                    subprocess.call("/home/pi/ir/sleep_tv.sh", shell=True)
                if start==True:
                    #START LIGHTS
                    print("Press OK")
                    subprocess.call("irsend SEND_ONCE LGTV OK", shell=True)

            #check if its a START LIGHT Command - Sleep
            if command=='action.devices.commands.BrightnessAbsolute':
                brightness=params.get("brightness", 50)

                if brightness>10:
                    if brightness==11:
                       volume=1
                    elif brightness==12:
                        volume=2
                    elif brightness==13:
                        volume=3
                    elif brightness==14:
                        volume=4
                    elif brightness==15:
                        volume=5
                    elif brightness==16:
                        volume=6
                    elif brightness==17:
                        volume=7
                    elif brightness==18:
                        volume=8
                    elif brightness==19:
                        volume=9
                    elif brightness==20:
                        volume=10

                    print("Set Volume DOWN by X: ",volume)
                    for x in xrange(volume):
                        subprocess.call("irsend SEND_ONCE LGTV VOL_DOWN", shell=True)
                        time.sleep(1)

                if brightness<10:
                    if brightness==1:
                       volume=1
                    elif brightness==2:
                        volume=2
                    elif brightness==3:
                        volume=3
                    elif brightness==4:
                        volume=4
                    elif brightness==5:
                        volume=5
                    elif brightness==6:
                        volume=6
                    elif brightness==7:
                        volume=7
                    elif brightness==8:
                        volume=8
                    elif brightness==9:
                        volume=9
                    elif brightness==10:
                        volume=10

                    print("Set Volume UP by X: ",volume)
                    for x in xrange(volume):
                        subprocess.call("irsend SEND_ONCE LGTV VOL_UP", shell=True)
                        time.sleep(1)


def register_device(project_id, credentials, device_model_id, device_id):
    """Register the device if needed.

    Registers a new assistant device if an instance with the given id
    does not already exists for this model.

    Args:
       project_id(str): The project ID used to register device instance.
       credentials(google.oauth2.credentials.Credentials): The Google
                OAuth2 credentials of the user to associate the device
                instance with.
       device_model_id(str): The registered device model ID.
       device_id(str): The device ID of the new instance.
    """
    base_url = '/'.join([DEVICE_API_URL, 'projects', project_id, 'devices'])
    device_url = '/'.join([base_url, device_id])
    session = google.auth.transport.requests.AuthorizedSession(credentials)
    r = session.get(device_url)
    print(device_url, r.status_code)
    if r.status_code == 404:
        print('Registering....')
        r = session.post(base_url, data=json.dumps({
            'id': device_id,
            'model_id': device_model_id,
            'client_type': 'SDK_LIBRARY'
        }))
        if r.status_code != 200:
            raise Exception('failed to register device: ' + r.text)
        print('\rDevice registered.')



def main():

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--credentials', type=existing_file,
                        metavar='OAUTH2_CREDENTIALS_FILE',
                        default=os.path.join(
                            os.path.expanduser('~/.config'),
                            'google-oauthlib-tool',
                            'credentials.json'
                        ),
                        help='Path to store and read OAuth2 credentials')
    parser.add_argument('--device_model_id', type=str,
                        metavar='DEVICE_MODEL_ID', required=True,
                        help='The device model ID registered with Google')
    parser.add_argument(
        '--project_id',
        type=str,
        metavar='PROJECT_ID',
        required=False,
        help='The project ID used to register device instances.')
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='%(prog)s ' +
        Assistant.__version_str__())

    args = parser.parse_args()
    with open(args.credentials, 'r') as f:
        credentials = google.oauth2.credentials.Credentials(token=None,
                                                            **json.load(f))

    with Assistant(credentials, args.device_model_id) as assistant:
        events = assistant.start()

        print('device_model_id:', args.device_model_id + '\n' +
              'device_id:', assistant.device_id + '\n')

        if args.project_id:
            register_device(args.project_id, credentials,
                            args.device_model_id, assistant.device_id)

        for event in events:
            process_event(event, assistant.device_id, assistant)

def get_trailing_number(s):
    m = re.search(r'\d+$', s)
    vol=int(m.group()) if m else 0
    #print("myvol - ",vol)

    if vol == 0:
        last_word = s.split()  # list of words
        #print("LAST WORD: ",last_word[-1])
        if last_word[-1]=="one":
            return 1
        elif last_word[-1]=="two":
            return 2
        elif last_word[-1]=="three":
            return 3
        elif last_word[-1]=="four":
            return 4
        elif last_word[-1]=="five":
            return 5
        elif last_word[-1]=="six":
            return 6
        elif last_word[-1]=="seven":
            return 7
        elif last_word[-1]=="eight":
            return 8
        elif last_word[-1]=="nine":
            return 9
        elif last_word[-1]=="ten":
            return 10
        else:
            return 3

    return vol

def say_ok():
    pickone=randint(0,10)

    if pickone == 0:
        say('done', lang="en-US", volume=50, pitch=200)
    elif pickone == 1:
        say('sure', lang="en-US", volume=50, pitch=200)
    elif pickone == 2:
        say('ok', lang="en-US", volume=50, pitch=200)
    elif pickone == 3:
        say('no problem', lang="en-US", volume=50, pitch=150)
    elif pickone == 4:
        say('you got it', lang="en-US", volume=50, pitch=200)
    elif pickone == 5:
        say('yes sir', lang="en-US", volume=50, pitch=150)
    elif pickone == 6:
        say('your the boss', lang="en-US", volume=50, pitch=150)
    elif pickone == 7:
        say('ya boy, sure', lang="en-US", volume=50, pitch=150)
    elif pickone == 8:
        say('yo mama', lang="en-US", volume=50, pitch=150)
    elif pickone == 9:
        say('yup', lang="en-US", volume=50, pitch=150)
    elif pickone == 10:
        say('i quit', lang="en-US", volume=50, pitch=175)




if __name__ == '__main__':
    main()
