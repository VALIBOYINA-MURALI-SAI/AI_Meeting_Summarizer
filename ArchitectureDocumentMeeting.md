# 📄 Architecture Document: Meeting Summarizer & Action Item Generator

---

## 1. 📱 Application Architecture

**Selected Architecture:** Serverless Architecture

### 🔧 Description:

In Serverless Architecture, the application is broken into multiple functions (or microservices) that are deployed to a cloud provider (e.g., AWS Lambda, Google Cloud Functions). These functions are event-driven, scale automatically, and do not require server management.

### ✅ Why Serverless?

- Pay-as-you-go model  
- Automatically scales with demand  
- Easy to integrate with APIs, file storage, and databases  
- Ideal for workflows like transcription, summarization, and task generation  

---

## 2. 🧩 Components

| **Component**              | **Description**                                                       |
|---------------------------|-----------------------------------------------------------------------|
| Frontend (Web UI)         | PyQt5 GUI or Web App (React in future), interacts with backend        |
| Audio Processor           | CLI script to record and store audio (`cli.py`)                       |
| Whisper Function          | Transcribes audio into text (using Whisper)                           |
| Summarization Function    | Summarizes transcript using BART or T5                                |
| Action Items Function     | Uses FLAN-T5 to extract action items from the summary                 |
| Storage (MongoDB)         | Stores transcripts, summaries, action items in collections            |
| Cloud API Gateway         | Manages endpoints to trigger serverless functions                     |
| Authentication            | Manages user login for future web version                             |

---

## 3. 💽 Database

### ER Diagram (MongoDB):

&nbsp;

<!-- Space left for diagram -->

&nbsp;

### Schema Design:

- `users`:  
  `{ userId, name, email }`

- `transcripts`:  
  `{ transcriptId, userId, text, timestamp }`

- `summaries`:  
  `{ summaryId, transcriptId, summaryText }`

- `action_items`:  
  `{ itemId, summaryId, taskText }`

---

## 4. 🔁 Data Exchange Contract

| **Item**         | **Description**                                                   |
|------------------|-------------------------------------------------------------------|
| Frequency        | Per session (audio uploaded/transcribed per use)                 |
| Data Sets        | Audio files (.mp3/.wav), transcript text, summary, action items   |
| Mode of Exchange | REST API, Local File System, MongoDB driver                       |
