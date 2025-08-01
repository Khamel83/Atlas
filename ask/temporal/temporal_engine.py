class TemporalEngine:
    def __init__(self, metadata_manager, config=None):
        self.metadata_manager = metadata_manager
        self.config = config or {}

    def find_temporal_relationships(self, max_delta_days=7):
        """
        Find temporal relationships using enhanced MetadataManager methods.
        Enhanced with deeper temporal analysis and pattern detection.
        """
        # Use the new temporal patterns method
        temporal_patterns = self.metadata_manager.get_temporal_patterns("week")

        # Get all metadata for relationship analysis
        all_items = self.metadata_manager.get_all_metadata()

        # Enhanced temporal relationship detection
        relationships = self._detect_temporal_clusters(all_items, max_delta_days)

        # Add temporal pattern insights
        insights = {
            "relationships": relationships,
            "temporal_patterns": temporal_patterns,
            "seasonal_insights": self._analyze_seasonal_patterns(temporal_patterns),
            "content_velocity": self._calculate_content_velocity(temporal_patterns),
        }

        return insights

    def _detect_temporal_clusters(self, all_items, max_delta_days):
        """
        Detect clusters of content created/updated in temporal proximity.
        """
        from datetime import datetime

        # Sort by created_at
        all_items.sort(key=lambda m: m.created_at)
        relationships = []

        for i in range(len(all_items) - 1):
            item1 = all_items[i]
            item2 = all_items[i + 1]
            try:
                t1 = datetime.fromisoformat(item1.created_at.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(item2.created_at.replace("Z", "+00:00"))
                delta_days = (t2 - t1).days

                if 0 < delta_days <= max_delta_days:
                    # Calculate relationship strength based on shared tags and content type
                    strength = self._calculate_relationship_strength(
                        item1, item2, delta_days
                    )

                    relationships.append(
                        {
                            "item1": item1,
                            "item2": item2,
                            "time_delta_days": delta_days,
                            "relationship_strength": strength,
                            "shared_tags": list(set(item1.tags) & set(item2.tags)),
                            "relationship_type": self._classify_relationship(
                                item1, item2
                            ),
                        }
                    )
            except (ValueError, AttributeError):
                continue

        return relationships

    def _calculate_relationship_strength(self, item1, item2, delta_days):
        """
        Calculate the strength of temporal relationship between two items.
        """
        strength = 1.0

        # Closer in time = stronger relationship (exponential decay)
        time_factor = 1.0 / (1.0 + delta_days * 0.5)
        strength *= time_factor

        # Shared tags increase strength
        shared_tags = set(item1.tags) & set(item2.tags)
        tag_factor = len(shared_tags) * 0.2
        strength += tag_factor

        # Same content type increases strength
        if item1.content_type == item2.content_type:
            strength += 0.3

        return min(strength, 2.0)  # Cap at 2.0

    def _classify_relationship(self, item1, item2):
        """
        Classify the type of temporal relationship.
        """
        shared_tags = set(item1.tags) & set(item2.tags)

        if len(shared_tags) >= 2:
            return "thematic_continuation"
        elif item1.content_type == item2.content_type:
            return "content_type_cluster"
        else:
            return "temporal_proximity"

    def _analyze_seasonal_patterns(self, temporal_patterns):
        """
        Analyze seasonal and cyclical patterns in content.
        """
        content_volume = temporal_patterns.get("content_volume", {})

        if len(content_volume) < 3:
            return {"insight": "Insufficient data for seasonal analysis"}

        # Simple seasonal analysis
        volumes = list(content_volume.values())
        avg_volume = sum(volumes) / len(volumes)
        peak_periods = [
            period
            for period, volume in content_volume.items()
            if volume > avg_volume * 1.5
        ]
        low_periods = [
            period
            for period, volume in content_volume.items()
            if volume < avg_volume * 0.5
        ]

        return {
            "average_volume": avg_volume,
            "peak_periods": peak_periods,
            "low_periods": low_periods,
            "volume_variance": max(volumes) - min(volumes) if volumes else 0,
        }

    def _calculate_content_velocity(self, temporal_patterns):
        """
        Calculate the velocity (rate of change) of content ingestion.
        """
        growth_analysis = temporal_patterns.get("growth_analysis", {})

        return {
            "growth_rate": growth_analysis.get("growth_rate_percent", 0),
            "trend": growth_analysis.get("trend", "unknown"),
            "recent_average": growth_analysis.get("recent_average", 0),
            "velocity_classification": self._classify_velocity(
                growth_analysis.get("growth_rate_percent", 0)
            ),
        }

    def _classify_velocity(self, growth_rate):
        """
        Classify content velocity based on growth rate.
        """
        if growth_rate > 50:
            return "accelerating"
        elif growth_rate > 10:
            return "growing"
        elif growth_rate > -10:
            return "stable"
        elif growth_rate > -50:
            return "declining"
        else:
            return "rapidly_declining"

    def get_time_aware_relationships(self, max_delta_days=1):
        """
        Legacy method for backward compatibility.
        """
        insights = self.find_temporal_relationships(max_delta_days)
        relationships = insights["relationships"]

        # Convert to old format
        return [
            (rel["item1"], rel["item2"], rel["time_delta_days"])
            for rel in relationships
        ]


# Example usage (for test/demo):
# engine = TemporalEngine(metadata_manager)
# rels = engine.get_time_aware_relationships(max_delta_days=2)
# for a, b, d in rels:
#     print(f"{a.title} -> {b.title} ({d} days)")
