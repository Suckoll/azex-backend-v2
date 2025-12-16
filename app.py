from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from twilio.twiml.voice_response import VoiceResponse, Gather
import requests

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

# ElevenLabs API key (get free at elevenlabs.io)
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')  # Add this in Render env vars
VOICE_ID = 'EXAVITQu4vr4xnSDxMaL'  # Bella — friendly female voice (premade, natural)

class BugReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.String(50))
    pest = db.Column(db.String(100))
    description = db.Column(db.String(500))
    reporter = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def speak_text(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    response = requests.post(url, json=data, headers=headers)
    if response.ok:
        return response.content
    return None

@app.route('/twilio/voice', methods=['POST'])
def twilio_voice():
    resp = VoiceResponse()

    # Friendly greeting
    gather = Gather(input='speech', action='/twilio/handle', method='POST', speech_timeout='auto')
    gather.say("Hello! Thank you for calling AZEX PestGuard. This is your virtual assistant. How can I help you today? For example, you can say 'I have a pest issue' or 'schedule a service'.", voice='woman', language='en-US')
    resp.append(gather)

    resp.say("We didn't hear anything. Goodbye.")
    resp.hangup()

    return Response(str(resp), mimetype='text/xml')

@app.route('/twilio/handle', methods=['POST'])
def twilio_handle():
    speech_result = request.values.get('SpeechResult', '').lower()
    caller_phone = request.values.get('From')

    resp = VoiceResponse()

    if 'pest' in speech_result or 'bug' in speech_result or 'issue' in speech_result:
        # Collect details
        session['report'] = {'phone': caller_phone}
        gather = Gather(input='speech', action='/twilio/report_unit', method='POST')
        gather.say("I'm sorry to hear that. Which apartment or unit number is the issue in?", voice='woman')
        resp.append(gather)
    else:
        resp.say("I didn't understand. Connecting you to a representative.")
        resp.dial('+16025551234')  # Replace with your office number

    return Response(str(resp), mimetype='text/xml')

# Add more /twilio/report_* routes for unit, pest, description, photo prompt, etc.

# For photo: send SMS with link to widget

@app.route('/')
def home():
    return "AZEX PestGuard Backend is LIVE!"

if __name__ == '__main__':
    app.run(debug=True)