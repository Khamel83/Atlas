class QuestionEngine:
    def __init__(self, content_analyzer=None):
        self.content_analyzer = content_analyzer

    def generate_questions(self, content):
        """
        Generate Socratic questions from content using a simple rule-based approach.
        For each sentence, generate 'Why', 'What', and 'How' questions.
        """
        import re
        # Split content into sentences (very basic)
        sentences = re.split(r'(?<=[.!?]) +', content.strip())
        questions = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            # Remove trailing punctuation for question templates
            base = sent.rstrip('.!?')
            questions.append(f"Why is '{base}' important?")
            questions.append(f"What are the implications of '{base}'?")
            questions.append(f"How does '{base}' relate to other ideas?")
        return questions

# Example usage (for test/demo):
# engine = QuestionEngine()
# qs = engine.generate_questions("The sky is blue. Water is wet.")
# for q in qs:
#     print(q) 