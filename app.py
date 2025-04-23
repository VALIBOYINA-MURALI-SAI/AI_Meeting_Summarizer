from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from bson import ObjectId
from forms import UploadForm
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
csrf = CSRFProtect(app)

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/meeting_summaries"
mongo = PyMongo(app)

# Import processing functions
from cli import transcribe_audio, summarize_transcript, action_items
from recording_manager import RecordingManager

recorder = RecordingManager()

@app.route('/')
def home():
    return render_template('main_dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if mongo.db.users.find_one({'username': username}):
            flash('Username already exists', 'danger')
        else:
            mongo.db.users.insert_one({
                'username': username,
                'password': generate_password_hash(password)
            })
            flash('Registration successful! Please login', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    summaries = list(mongo.db.summaries.find({'user_id': ObjectId(session['user_id'])}))

    # Convert ObjectId to string for each summary
    for summary in summaries:
        summary['_id'] = str(summary['_id'])
        summary['user_id'] = str(summary['user_id'])

    form = UploadForm()
    return render_template('dashboard.html',
                         username=user['username'],
                         summaries=summaries,
                         form=form)

@app.route('/start_recording', methods=["GET", 'POST'])
def start_recording():
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    filename = f"uploads/meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    session['recording_file'] = filename
    global recorder
    recorder.output_filename = filename
    recorder.start_recording()

    flash("🎙️ Recording started!", "info")
    return redirect(url_for('dashboard'))


@app.route('/stop_recording', methods=["GET", 'POST'])
def stop_recording():
    filename = session.get('recording_file')
    if not filename:
        flash("⚠️ No recording session found.", "danger")
        return redirect(url_for('dashboard'))

    global recorder
    recorder.stop_recording()

    if not os.path.exists(filename):
        flash("⚠️ No recording found to stop.", "danger")
        return redirect(url_for('dashboard'))

    transcript = transcribe_audio(filename)
    summary = summarize_transcript(transcript)
    extracted_items = action_items(transcript)  # Changed variable name

    mongo.db.summaries.insert_one({
        'user_id': ObjectId(session['user_id']),
        'username': session['username'],
        'title': f"Recorded Meeting on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        'summary': summary,
        'action_items': extracted_items,  # Use the new variable name
        'transcript': transcript,
        'timestamp': datetime.utcnow()
    })

    flash("✅ Recording stopped and summary saved.", "success")
    return redirect(url_for('dashboard'))

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    form = UploadForm()
    if form.validate_on_submit():
        audio = form.audio_file.data
        filename = f"uploads/{datetime.now().strftime('%Y%m%d%H%M%S')}_{audio.filename}"
        audio.save(filename)
        
        try:
            transcript = transcribe_audio(filename)
            summary = summarize_transcript(transcript)
            items = action_items(transcript)
            
            mongo.db.summaries.insert_one({
                'user_id': ObjectId(session['user_id']),
                'username': session['username'],
                'title': f"Uploaded Meeting {datetime.now().strftime('%Y-%m-%d')}",
                'summary': summary,
                'action_items': items,
                'transcript': transcript,
                'timestamp': datetime.now()
            })
            
            flash("✅ Audio processed and saved!", "success")
        except Exception as e:
            flash(f"Error processing audio: {str(e)}", "danger")
    else:
        flash("Invalid file upload", "danger")
    
    return redirect(url_for('dashboard'))


@app.route('/save_summary', methods=['POST','get'])
def save_summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title')
    summary = request.form.get('summary')
    action_items = request.form.get('action_items', '')

    if not title or not summary:
        flash('Title and summary are required', 'danger')
        return redirect(url_for('dashboard'))

    action_items_list = [item.strip() for item in action_items.split('\n') if item.strip()]

    mongo.db.summaries.insert_one({
        'user_id': ObjectId(session['user_id']),
        'username': session['username'],
        'title': title,
        'summary': summary,
        'action_items': action_items_list,
        'timestamp': datetime.now()
    })

    flash('Summary saved successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_summary', methods=['POST'])
def edit_summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    summary_id = request.form['summary_id']
    updated_text = request.form['summary_text']
    
    mongo.db.summaries.update_one(
        {'_id': ObjectId(summary_id), 'user_id': ObjectId(session['user_id'])},
        {'$set': {'summary': updated_text}}
    )
    
    flash("✏️ Summary updated successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_summary/<summary_id>')
def delete_summary(summary_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    mongo.db.summaries.delete_one({
        '_id': ObjectId(summary_id),
        'user_id': ObjectId(session['user_id'])
    })
    
    flash("🗑️ Summary deleted successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/get-started')
def get_started():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('register'))

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)