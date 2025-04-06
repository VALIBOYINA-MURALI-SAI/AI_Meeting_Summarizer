def extract_action_items(text: str) -> list:
    print("✅ Extracting Action Items (Rule-Based)...")
    keywords = ["will", "can", "must", "should", "need to", "task", "complete", "email", "send", "assign", "handle", "reach out"]
    lines = text.split("\n")
    action_items = []
    for line in lines:
        if any(keyword in line.lower() for keyword in keywords):
            action_items.append(line.strip())
    return action_items
