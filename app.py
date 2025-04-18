import os
from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from bson import ObjectId
from forms import UploadForm
import subprocess

# Import necessary functions from cli.py
from cli import transcribe_audio, summarize_transcript, save_results_to_file
# app.py
from action_item_generator import extract_action_items  # Add this line to import the function
from recording_manager import RecordingManager

recorder = RecordingManager()


app = Flask(__name__)
# Initialize CSRF protection
csrf = CSRFProtect(app)
app.secret_key = os.urandom(24)  # Keep it secure

# MongoDB URI
app.config["MONGO_URI"] = "mongodb://localhost:27017/meeting_summaries"
mongo = PyMongo(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user exists
        user = mongo.db.users.find_one({'username': username})
        if user is not None:
            if 'password' in user and check_password_hash(user['password'], password):
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        else:
            flash('User not found.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if user already exists
        if mongo.db.users.find_one({'username': username}):
            return render_template('register.html', error="Username already exists.")
        
        # Use generate_password_hash ONLY (no bcrypt)
        password_hash = generate_password_hash(password)
        mongo.db.users.insert_one({'username': username, 'password': password_hash})
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()  # Clears all session data
    return redirect(url_for('login'))  # Redirect to login page

@app.route('/save_summary', methods=['POST'])
def save_summary():
    if 'username' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title')
    summary = request.form.get('summary')
    action_items = request.form.get('action_items', '')

    if not title or not summary:
        return "Missing title or summary", 400

    action_items_list = [item.strip() for item in action_items.split('\n') if item.strip()]

    new_entry = {
        "user_id": ObjectId(session['user_id']),
        "username": session['username'],
        "title": title,
        "summary": summary,
        "action_items": action_items_list,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    mongo.db.summaries.insert_one(new_entry)
    return redirect(url_for('dashboard'))


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    form = UploadForm()
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    summaries = list(mongo.db.summaries.find({'user_id': ObjectId(session['user_id'])}))

    # 🔥 Convert ObjectId to string
    for summary in summaries:
        summary['_id'] = str(summary['_id'])
        summary['user_id'] = str(summary['user_id'])

    return render_template('dashboard.html', username=user['username'], summaries=summaries, form=form)


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
    action_items = extract_action_items(summary)

    mongo.db.summaries.insert_one({
        'user_id': ObjectId(session['user_id']),
        'username': session['username'],
        'title': f"Recorded Meeting on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        'summary': summary,
        'action_items': action_items,
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
    if not form.validate_on_submit():
        flash('Invalid file or CSRF token missing.', 'danger')
        return redirect(url_for('dashboard'))

    audio = form.audio_file.data
    filename = audio.filename
    file_path = os.path.join('uploads', filename)
    audio.save(file_path)

    transcript = transcribe_audio(file_path)
    summary = summarize_transcript(transcript)
    action_items = extract_action_items(summary)

    mongo.db.summaries.insert_one({
        'user_id': ObjectId(session['user_id']),
        'username': session['username'],
        'title': f"Meeting on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        'summary': summary,
        'action_items': action_items,
        'transcript': transcript,
        'timestamp': datetime.utcnow()
    })

    flash("📝 Transcription and summary added successfully.", "success")
    return redirect(url_for('dashboard'))  # ← redirect instead of jsonify

@app.route("/summaries")
def my_summaries():
    user_id = ObjectId(session['user_id'])
    summaries = list(mongo.db.summaries.find({'user_id': user_id}))
    return render_template("my_summaries.html", summaries=summaries)

@app.route("/delete_summary/<summary_id>")
def delete_summary(summary_id):
    mongo.db.summaries.delete_one({"_id": ObjectId(summary_id)})
    flash("🗑️ Summary deleted successfully!", "success")
    return redirect(url_for("my_summaries"))

@app.route("/edit_summary", methods=["POST"])
def edit_summary():
    summary_id = request.form['summary_id']
    updated_text = request.form['summary_text']
    mongo.db.summaries.update_one(
        {"_id": ObjectId(summary_id)},
        {"$set": {"summary": updated_text}}
    )
    flash("✏️ Summary updated successfully!", "success")
    return redirect(url_for("my_summaries"))


if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
