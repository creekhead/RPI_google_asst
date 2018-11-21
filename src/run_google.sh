echo Make sure to stop the AssistantPi service first - service AssistantPi stop
source env/bin/activate
python google_assistant.py --credentials ~/.config/google-oauthlib-tool/credentials.json --device_model_id agassists-v1-assist-v1-ixbge
