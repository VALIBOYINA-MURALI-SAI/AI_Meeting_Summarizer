# forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField
from wtforms.validators import DataRequired

class UploadForm(FlaskForm):
    audio_file = FileField('Audio File', validators=[
        FileRequired(),
        FileAllowed(['mp3', 'wav', 'm4a', 'flac'], 'Audio files only!')
    ])
    submit = SubmitField('Upload & Summarize')
