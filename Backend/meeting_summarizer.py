import torch
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
import re
import nltk
from functools import lru_cache
import logging

nltk.download('punkt', quiet=True)
logging.basicConfig(level=logging.INFO)

class MeetingProcessor:
    def __init__(self):
        self.model_loaded = False
        try:
            # Try loading smaller model first
            self.model_name = "google/flan-t5-small"
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )
            self.model_loaded = True
            logging.info("Successfully loaded flan-t5-small model")
        except Exception as e:
            logging.warning(f"Could not load model: {e}")
            self.model_loaded = False

    def clean_transcript(self, text):
        """Lightweight text cleaning"""
        text = re.sub(r'\b(um|uh|ah|like|you know)\b', '', text, flags=re.IGNORECASE)
        return text[:5000]  # Limit input size

    def extract_action_items(self, transcript):
        """Hybrid approach with fallback"""
        clean_text = self.clean_transcript(transcript)
        
        if not self.model_loaded:
            return self._fallback_action_items(clean_text)
            
        try:
            inputs = self.tokenizer(
                f"Extract action items: {clean_text}",
                return_tensors="pt",
                max_length=512,
                truncation=True
            )
            
            outputs = self.model.generate(
                inputs["input_ids"],
                max_length=150,
                num_beams=2,
                early_stopping=True
            )
            
            result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return self._post_process_items(result.split("; "))
        except Exception as e:
            logging.error(f"Model processing failed: {e}")
            return self._fallback_action_items(clean_text)

    def _fallback_action_items(self, text):
        """Lightweight fallback when model can't load"""
        action_words = ["will", "should", "assign", "task", "prepare", 
                       "review", "submit", "by", "action", "next steps"]
        sentences = nltk.sent_tokenize(text)
        return [s for s in sentences if any(word in s.lower() for word in action_words)][:5] or ["No clear action items"]

    def _post_process_items(self, items):
        """Clean and format items"""
        return [item.strip().capitalize() for item in items if item.strip()]