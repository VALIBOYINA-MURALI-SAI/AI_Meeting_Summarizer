from transformers import pipeline
import re

summarizer = pipeline("text2text-generation", model="google/flan-t5-large")

def extract_action_items(transcript):
    # Clean the transcript first
    clean_transcript = re.sub(r'\b(um|uh|ah|like|you know)\b', '', transcript, flags=re.IGNORECASE)
    clean_transcript = re.sub(r'\[.*?\]|\(.*?\)', '', clean_transcript)  # Remove anything in brackets
    
    # More focused prompt
    prompt = f"""Extract ONLY specific, actionable tasks from this meeting discussion.
    Format each as: "• [Person] Task (Deadline)"
    Include ONLY items that are:
    - Assignments given to someone
    - Decisions requiring follow-up
    - Concrete next steps
    - Tasks with clear owners
    
    EXCLUDE:
    - General discussions
    - Philosophical statements
    - Hypothetical scenarios
    - Opinions without actions
    
    Transcript: {clean_transcript}
    
    Action Items:"""
    
    try:
        # Generate with more constrained parameters
        action_output = summarizer(
            prompt,
            max_length=300,
            min_length=30,
            do_sample=False,
            temperature=0.2,  # Lower temperature for less randomness
            top_k=30,
            no_repeat_ngram_size=3,
            early_stopping=True
        )
        
        # Process the output
        raw_items = [item.strip() for item in action_output[0]['generated_text'].split("\n") if item.strip()]
        
        # Filter and format items
        final_items = []
        for item in raw_items:
            # Skip template lines and invalid items
            if not item.startswith("•") or len(item) < 10:
                continue
                
            # Clean up the item
            item = re.sub(r'\s+', ' ', item)  # Remove extra spaces
            item = item.replace('• •', '•')    # Fix double bullets
            
            # Ensure proper formatting
            if not item.endswith(('.', '!', '?')):
                item += '.'
                
            final_items.append(item)
            
        return final_items[:10] if final_items else ["No clear action items identified"]
        
    except Exception as e:
        print(f"⚠️ Error extracting action items: {e}")
        return ["Error processing action items"]