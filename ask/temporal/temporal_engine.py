class TemporalEngine:
    def __init__(self, metadata_manager):
        self.metadata_manager = metadata_manager

    def get_time_aware_relationships(self, max_delta_days=1):
        """
        Return pairs of content items where one was created/updated soon after another (within max_delta_days).
        Returns a list of tuples: (item1, item2, time_delta_days)
        """
        from datetime import datetime
        all_items = []
        for content_type in self.metadata_manager.ContentType:
            all_items.extend(self.metadata_manager.get_all_metadata(content_type))
        # Sort by created_at
        all_items.sort(key=lambda m: m.created_at)
        relationships = []
        for i in range(len(all_items) - 1):
            item1 = all_items[i]
            item2 = all_items[i+1]
            t1 = datetime.fromisoformat(item1.created_at.replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(item2.created_at.replace('Z', '+00:00'))
            delta_days = (t2 - t1).days
            if 0 < delta_days <= max_delta_days:
                relationships.append((item1, item2, delta_days))
        return relationships

# Example usage (for test/demo):
# engine = TemporalEngine(metadata_manager)
# rels = engine.get_time_aware_relationships(max_delta_days=2)
# for a, b, d in rels:
#     print(f"{a.title} -> {b.title} ({d} days)") 