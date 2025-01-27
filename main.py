from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory
from werkzeug.utils import secure_filename
from google.cloud import speech, texttospeech
from pydub import AudioSegment
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files():
    wav_files = []
    tts_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):  
            wav_files.append(filename)

    tts_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'tts')
    if os.path.exists(tts_folder):
        for filename in os.listdir(tts_folder):
            if filename.endswith('.wav'):
                tts_files.append(f"tts/{filename}")

    wav_files.sort(reverse=True)
    tts_files.sort(reverse=True)
    return wav_files, tts_files

@app.route('/')
def index():
    wav_files, tts_files = get_files()
    return render_template('index.html', wav_files=wav_files, tts_files=tts_files)


@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)
    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        with open(file_path, 'rb') as audio_file:
            audio_content = audio_file.read()

        client = speech.SpeechClient()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            language_code="en-US",  
            model="latest_long",  
            enable_word_confidence=True,
            enable_word_time_offsets=True
        )

        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=90)

        transcript = ''
        for result in response.results:
            transcript += result.alternatives[0].transcript + '\n'

        transcript_file_path = file_path.replace('.wav', '.txt')
        with open(transcript_file_path, 'w') as transcript_file:
            transcript_file.write(transcript)

    return redirect('/')  


@app.route('/upload/<filename>')
def get_file(filename):
    return send_file(filename)

    
@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    tts_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'tts')
    os.makedirs(tts_folder, exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
    tts_path = os.path.join(tts_folder, filename)

    with open(tts_path, 'wb') as out:
        out.write(response.audio_content)

    return redirect('/')

@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)