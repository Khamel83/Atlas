class QuestionEngine:
    def __init__(self, metadata_manager=None, config=None):
        self.metadata_manager = metadata_manager
        self.config = config or {}

    def generate_questions(self, content, metadata=None):
        """
        Generate contextually relevant Socratic questions enhanced with metadata analysis.
        """
        import re
        
        # Enhanced question generation using metadata context
        questions = []
        
        # Basic content-based questions
        content_questions = self._generate_content_questions(content)
        questions.extend(content_questions)
        
        # Metadata-enhanced questions
        if metadata and self.metadata_manager:
            context_questions = self._generate_contextual_questions(metadata)
            questions.extend(context_questions)
            
            # Cross-content relationship questions
            relationship_questions = self._generate_relationship_questions(metadata)
            questions.extend(relationship_questions)
        
        # Remove duplicates and return
        return list(dict.fromkeys(questions))  # Preserves order while removing duplicates

    def _generate_content_questions(self, content):
        """
        Generate basic questions from content text.
        """
        import re
        
        # Split content into sentences
        sentences = re.split(r'(?<=[.!?]) +', content.strip())
        questions = []
        
        # Limit to prevent overwhelming number of questions
        for sent in sentences[:3]:  # Only first 3 sentences
            sent = sent.strip()
            if not sent or len(sent) < 10:
                continue
                
            # Remove trailing punctuation
            base = sent.rstrip('.!?')
            
            # Enhanced question templates
            questions.extend([
                f"Why is '{base}' significant?",
                f"What evidence supports '{base}'?", 
                f"How does '{base}' connect to broader themes?",
                f"What questions does '{base}' raise?",
                f"What would happen if '{base}' were not true?"
            ])
            
        return questions[:10]  # Limit to prevent overload

    def _generate_contextual_questions(self, metadata):
        """
        Generate questions based on content metadata and context.
        """
        questions = []
        
        # Tag-based questions
        if metadata.tags:
            primary_tags = metadata.tags[:3]  # Focus on first few tags
            for tag in primary_tags:
                questions.extend([
                    f"How does this content relate to other '{tag}' materials?",
                    f"What makes this '{tag}' content unique?",
                    f"What are the key insights about '{tag}' here?"
                ])
        
        # Content type specific questions
        content_type = metadata.content_type.value
        type_questions = {
            'article': [
                "What is the main argument presented?",
                "What evidence is most compelling?",
                "How does this challenge conventional thinking?"
            ],
            'youtube': [
                "What are the key visual or audio elements?",
                "How does the presentation style affect the message?",
                "What would you tell someone who couldn't watch this?"
            ],
            'podcast': [
                "What makes this conversation valuable?",
                "How do the speakers' perspectives differ?",
                "What questions would you ask the host/guest?"
            ]
        }
        
        questions.extend(type_questions.get(content_type, []))
        
        # Time-based questions
        try:
            from datetime import datetime
            created_date = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
            days_old = (datetime.now() - created_date).days
            
            if days_old > 30:
                questions.append("How has your understanding of this topic evolved since encountering this content?")
            if days_old > 90:
                questions.append("What from this content remains most relevant today?")
                
        except (ValueError, AttributeError):
            pass
        
        return questions

    def _generate_relationship_questions(self, metadata):
        """
        Generate questions based on relationships to other content.
        """
        if not self.metadata_manager:
            return []
            
        questions = []
        
        # Find related content by tags
        if metadata.tags:
            # Get content with similar tags
            related_content = []
            for tag in metadata.tags[:2]:  # Check top 2 tags
                filters = {'tags': [tag]}
                tagged_content = self.metadata_manager.get_all_metadata(filters)
                related_content.extend([item for item in tagged_content if item.uid != metadata.uid])
            
            if related_content:
                questions.extend([
                    "How does this content compare to other materials on similar topics?",
                    "What patterns do you notice across related content?",
                    "What gaps exist between this and related materials?"
                ])
        
        # Temporal relationship questions
        if hasattr(self.metadata_manager, 'get_temporal_patterns'):
            temporal_patterns = self.metadata_manager.get_temporal_patterns()
            
            # Check if this content was part of a learning cluster
            content_volume = temporal_patterns.get('content_volume', {})
            if content_volume:
                # Find the time period when this content was created
                from datetime import datetime
                try:
                    created_date = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
                    period_key = created_date.strftime('%Y-%m')
                    
                    period_volume = content_volume.get(period_key, 0)
                    if period_volume > 3:  # High activity period
                        questions.append("What was driving your interest in this topic during this time period?")
                        
                except (ValueError, AttributeError):
                    pass
        
        return questions

    def generate_progressive_questions(self, metadata, difficulty_level=1):
        """
        Generate questions with progressive difficulty levels.
        
        Args:
            metadata: ContentMetadata object
            difficulty_level: 1 (basic) to 5 (advanced)
        """
        # Load content if available
        content = self._load_content_text(metadata)
        if not content:
            content = metadata.title or "content"
        
        base_questions = self.generate_questions(content, metadata)
        
        # Filter and enhance based on difficulty level
        if difficulty_level == 1:
            # Basic comprehension
            filtered = [q for q in base_questions if any(word in q.lower() for word in ['what', 'who', 'when', 'where'])]
        elif difficulty_level == 2:
            # Application
            filtered = [q for q in base_questions if any(word in q.lower() for word in ['how', 'why', 'relates'])]
        elif difficulty_level == 3:
            # Analysis
            filtered = [q for q in base_questions if any(word in q.lower() for word in ['compare', 'contrast', 'evidence', 'patterns'])]
        elif difficulty_level == 4:
            # Synthesis
            filtered = [q for q in base_questions if any(word in q.lower() for word in ['connect', 'integrate', 'relationship'])]
        else:  # difficulty_level == 5
            # Evaluation
            filtered = [q for q in base_questions if any(word in q.lower() for word in ['evaluate', 'critique', 'challenge', 'implications'])]
        
        return filtered[:5]  # Return top 5 for focused learning

    def _load_content_text(self, metadata):
        """
        Attempt to load the actual content text for better question generation.
        """
        if not metadata.content_path:
            return None
            
        try:
            import os
            if os.path.exists(metadata.content_path):
                with open(metadata.content_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Return first 1000 characters for question generation
                    return content[:1000]
        except Exception:
            pass
            
        return None

    def get_question_analytics(self):
        """
        Get analytics about question generation and user engagement.
        """
        if not self.metadata_manager:
            return {'error': 'No metadata manager available'}
        
        all_metadata = self.metadata_manager.get_all_metadata()
        
        # Analyze question generation potential
        questionable_content = 0
        total_tags = 0
        
        for metadata in all_metadata:
            if metadata.content_path or metadata.title:
                questionable_content += 1
            total_tags += len(metadata.tags)
        
        return {
            'total_content_items': len(all_metadata),
            'questionable_content': questionable_content,
            'average_tags_per_item': total_tags / max(len(all_metadata), 1),
            'question_generation_coverage': questionable_content / max(len(all_metadata), 1)
        }

# Example usage (for test/demo):
# engine = QuestionEngine()
# qs = engine.generate_questions("The sky is blue. Water is wet.")
# for q in qs:
#     print(q) 