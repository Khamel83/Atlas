class RecallEngine:
    def __init__(self, metadata_manager):
        self.metadata_manager = metadata_manager

    def schedule_spaced_repetition(self, n=5):
        """
        Return up to n content items most overdue for review based on spaced repetition intervals.
        Uses 'last_reviewed' in type_specific if present, else falls back to updated_at.
        """
        from datetime import datetime, timedelta
        intervals = [1, 3, 7, 14, 30]  # days
        all_items = []
        for content_type in self.metadata_manager.ContentType:
            all_items.extend(self.metadata_manager.get_all_metadata(content_type))
        now = datetime.now()
        overdue = []
        for item in all_items:
            last = item.type_specific.get('last_reviewed') if hasattr(item, 'type_specific') and item.type_specific else None
            if not last:
                last = getattr(item, 'updated_at', None)
            if not last:
                continue
            try:
                last_dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
            except Exception:
                continue
            # Determine which interval this item is on (default: first)
            review_count = item.type_specific.get('review_count', 0) if hasattr(item, 'type_specific') and item.type_specific else 0
            interval_days = intervals[min(review_count, len(intervals)-1)]
            due_date = last_dt + timedelta(days=interval_days)
            if now >= due_date:
                overdue.append((item, (now - due_date).days))
        overdue.sort(key=lambda x: x[1], reverse=True)  # Most overdue first
        return [item for item, _ in overdue[:n]]

    def mark_reviewed(self, content_metadata):
        """
        Mark a content item as reviewed (update last_reviewed and increment review_count).
        """
        from datetime import datetime
        if not hasattr(content_metadata, 'type_specific') or content_metadata.type_specific is None:
            content_metadata.type_specific = {}
        content_metadata.type_specific['last_reviewed'] = datetime.now().isoformat()
        content_metadata.type_specific['review_count'] = content_metadata.type_specific.get('review_count', 0) + 1
        self.metadata_manager.save_metadata(content_metadata)

# Example usage (for test/demo):
# engine = RecallEngine(metadata_manager)
# due = engine.schedule_spaced_repetition(n=3)
# for item in due:
#     print(item.title, item.type_specific.get('last_reviewed'))
#     engine.mark_reviewed(item) 