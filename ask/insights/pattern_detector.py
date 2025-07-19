class PatternDetector:
    def __init__(self, metadata_manager):
        self.metadata_manager = metadata_manager

    def find_patterns(self, n=3):
        """
        Find the most common tags and sources across the content corpus.
        Returns a dict with top N tags and sources.
        """
        from collections import Counter
        all_items = []
        for content_type in self.metadata_manager.ContentType:
            all_items.extend(self.metadata_manager.get_all_metadata(content_type))
        tag_counter = Counter()
        source_counter = Counter()
        for item in all_items:
            tags = getattr(item, 'tags', [])
            tag_counter.update(tags)
            source = getattr(item, 'source', None)
            if source:
                source_counter.update([source])
        return {
            'top_tags': tag_counter.most_common(n),
            'top_sources': source_counter.most_common(n)
        }

# Example usage (for test/demo):
# detector = PatternDetector(metadata_manager)
# patterns = detector.find_patterns(n=5)
# print(patterns) 