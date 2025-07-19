class ProactiveSurfacer:
    def __init__(self, metadata_manager):
        self.metadata_manager = metadata_manager

    def surface_forgotten_content(self, n=5, cutoff_days=30):
        """
        Return up to n content items not updated in the last cutoff_days.
        """
        forgotten = self.metadata_manager.get_forgotten_content(cutoff_days)
        return forgotten[:n]

    def mark_surfaced(self, content_metadata):
        """
        Mark a content item as surfaced (update its updated_at timestamp).
        """
        from datetime import datetime
        content_metadata.updated_at = datetime.now().isoformat()
        self.metadata_manager.save_metadata(content_metadata)

# Example usage (for test/demo):
# surfacer = ProactiveSurfacer(metadata_manager)
# forgotten = surfacer.surface_forgotten_content(n=3)
# for item in forgotten:
#     print(item.title, item.updated_at)
#     surfacer.mark_surfaced(item) 