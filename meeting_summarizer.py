from transformers import pipeline

# Initialize the summarization pipeline with a conversation-optimized model
summarizer = pipeline("summarization", model="philschmid/bart-large-cnn-samsum")

# Sample meeting transcript (replace this with dynamic input later)
transcript = """
Alice: Let's finish the report by Friday.
Bob: Sure, I'll handle the charts.
Alice: Can you also reach out to the marketing team?
Bob: Okay, I’ll email them today.
Charlie: I’ll take care of proofreading.
"""

# Generate summary
summary_output = summarizer(transcript, max_length=130, min_length=30, do_sample=False)
summary = summary_output[0]['summary_text']

print("\n📝 Meeting Summary:\n")
print(summary)

# Action item extraction (basic rule-based for now)
def extract_action_items(text):
    keywords = ["will", "can", "must", "should", "need to", "task", "complete", "email", "send", "assign", "handle", "reach out"]
    lines = text.split("\n")
    action_items = []
    for line in lines:
        if any(keyword in line.lower() for keyword in keywords):
            action_items.append(line.strip())
    return action_items

print("\n✅ Action Items:\n")
for idx, item in enumerate(extract_action_items(transcript), 1):
    print(f"{idx}. {item}")
