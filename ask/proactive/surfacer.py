class ProactiveSurfacer:
    def __init__(self, metadata_manager, config=None):
        self.metadata_manager = metadata_manager
        self.config = config or {}
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = self.config.get('cache_ttl_seconds', 300)  # 5 minutes default

    def surface_forgotten_content(self, n=5, cutoff_days=30):
        """
        Return up to n content items not updated in the last cutoff_days.
        Enhanced with caching and improved ranking.
        """
        from datetime import datetime, timedelta
        
        # Check cache validity
        now = datetime.now()
        cache_key = f"forgotten_{n}_{cutoff_days}"
        
        if (self._cache_timestamp and 
            cache_key in self._cache and 
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl):
            return self._cache[cache_key]
        
        # Get forgotten content with enhanced ranking
        forgotten = self.metadata_manager.get_forgotten_content(cutoff_days)
        
        # Apply additional ranking factors
        enhanced_forgotten = []
        for metadata in forgotten:
            # Calculate enhanced relevance score
            relevance_score = self._calculate_relevance_score(metadata)
            enhanced_forgotten.append({
                'metadata': metadata,
                'relevance_score': relevance_score
            })
        
        # Sort by relevance score (highest first)
        enhanced_forgotten.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Extract top n items
        result = [item['metadata'] for item in enhanced_forgotten[:n]]
        
        # Cache the result
        self._cache[cache_key] = result
        self._cache_timestamp = now
        
        return result

    def _calculate_relevance_score(self, metadata):
        """
        Calculate enhanced relevance score for content item.
        """
        score = 0.0
        
        # Base score from content type
        type_scores = {
            'article': 1.0,
            'youtube': 0.8,
            'podcast': 0.7,
            'instapaper': 0.9
        }
        score += type_scores.get(metadata.content_type.value, 0.5)
        
        # Boost for tagged content (more processed = more valuable)
        score += len(metadata.tags) * 0.1
        
        # Boost for content with notes (user engagement)
        score += len(metadata.notes) * 0.2
        
        # Boost for successful processing
        if metadata.status.value == 'success':
            score += 0.3
        
        # Penalty for error status
        if metadata.status.value == 'error':
            score -= 0.5
        
        # Time-based relevance (older content gets slight boost for rediscovery)
        try:
            from datetime import datetime
            created_date = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
            days_old = (datetime.now() - created_date).days
            
            # Sweet spot around 30-90 days old
            if 30 <= days_old <= 90:
                score += 0.2
            elif 7 <= days_old <= 180:
                score += 0.1
        except (ValueError, AttributeError):
            pass
        
        return max(score, 0.0)  # Ensure non-negative

    def mark_surfaced(self, content_metadata):
        """
        Mark a content item as surfaced (update its updated_at timestamp).
        Also invalidates cache to ensure fresh results.
        """
        from datetime import datetime
        content_metadata.updated_at = datetime.now().isoformat()
        self.metadata_manager.save_metadata(content_metadata)
        
        # Invalidate cache
        self._cache.clear()
        self._cache_timestamp = None

    def get_surfacing_stats(self):
        """
        Get statistics about content surfacing patterns.
        """
        # Get all metadata to analyze patterns
        all_metadata = self.metadata_manager.get_all_metadata()
        
        total_items = len(all_metadata)
        if total_items == 0:
            return {
                'total_items': 0,
                'forgotten_30_days': 0,
                'forgotten_60_days': 0,
                'forgotten_90_days': 0,
                'never_surfaced': 0,
                'avg_days_since_update': 0
            }
        
        from datetime import datetime
        now = datetime.now()
        
        forgotten_30 = len(self.metadata_manager.get_forgotten_content(30))
        forgotten_60 = len(self.metadata_manager.get_forgotten_content(60))
        forgotten_90 = len(self.metadata_manager.get_forgotten_content(90))
        
        # Calculate average days since update
        total_days = 0
        valid_items = 0
        for metadata in all_metadata:
            try:
                updated_date = datetime.fromisoformat(metadata.updated_at.replace('Z', '+00:00'))
                days_since_update = (now - updated_date).days
                total_days += days_since_update
                valid_items += 1
            except (ValueError, AttributeError):
                continue
        
        avg_days = total_days / valid_items if valid_items > 0 else 0
        
        return {
            'total_items': total_items,
            'forgotten_30_days': forgotten_30,
            'forgotten_60_days': forgotten_60, 
            'forgotten_90_days': forgotten_90,
            'never_surfaced': forgotten_90,  # Items not updated in 90 days
            'avg_days_since_update': avg_days,
            'cache_hit_rate': len(self._cache) / max(1, len(self._cache) + 1)  # Rough cache efficiency
        }

    def clear_cache(self):
        """
        Manually clear the surfacing cache.
        """
        self._cache.clear()
        self._cache_timestamp = None

# Example usage (for test/demo):
# surfacer = ProactiveSurfacer(metadata_manager)
# forgotten = surfacer.surface_forgotten_content(n=3)
# for item in forgotten:
#     print(item.title, item.updated_at)
#     surfacer.mark_surfaced(item) 