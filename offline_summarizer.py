from transformers import pipeline
import nltk

# Download sentence tokenizer if not already downloaded
nltk.download("punkt")
from nltk.tokenize import sent_tokenize

# Initialize model
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def split_text(text, max_chunk_tokens=500):
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for sentence in sentences:
        tokens = len(sentence.split())

        if current_tokens + tokens <= max_chunk_tokens:
            current_chunk += " " + sentence
            current_tokens += tokens
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_tokens = tokens

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def summarize_text_offline(text):
    chunks = split_text(text)
    summarized_chunks = []

    for chunk in chunks:
        summary = summarizer(chunk, max_length=130, min_length=30, do_sample=False)
        summarized_chunks.append(summary[0]['summary_text'])

    return "\n".join(summarized_chunks)
