class PatternDetector:
    def __init__(self, metadata_manager, config=None):
        self.metadata_manager = metadata_manager
        self.config = config or {}
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = self.config.get(
            "cache_ttl_seconds", 600
        )  # 10 minutes default

    def detect_tag_patterns(self, min_frequency=2):
        """
        Detect tag usage patterns and trends using new MetadataManager methods.
        Enhanced with trend detection and alerts.
        """
        from datetime import datetime

        # Check cache validity
        now = datetime.now()
        cache_key = f"tag_patterns_{min_frequency}"

        if (
            self._cache_timestamp
            and cache_key in self._cache
            and (now - self._cache_timestamp).total_seconds() < self._cache_ttl
        ):
            return self._cache[cache_key]

        # Get comprehensive tag patterns from MetadataManager
        patterns = self.metadata_manager.get_tag_patterns(min_frequency)

        # Enhance with trend analysis
        enhanced_patterns = self._enhance_with_trends(patterns)

        # Add pattern visualization data
        enhanced_patterns["visualization_data"] = self._create_visualization_data(
            patterns
        )

        # Add trending alerts
        enhanced_patterns["alerts"] = self._generate_trending_alerts(patterns)

        # Cache the result
        self._cache[cache_key] = enhanced_patterns
        self._cache_timestamp = now

        return enhanced_patterns

    def _enhance_with_trends(self, patterns):
        """
        Enhance patterns with trend analysis over time.
        """
        enhanced = patterns.copy()

        # Get temporal patterns to analyze tag trends over time
        temporal_patterns = self.metadata_manager.get_temporal_patterns("month")
        tag_trends = temporal_patterns.get("tag_trends", {})

        # Analyze trending direction for each tag
        enhanced["tag_trend_analysis"] = {}

        for tag in patterns["tag_frequencies"]:
            trend_data = []
            for period, period_tags in tag_trends.items():
                count = period_tags.get(tag, 0)
                trend_data.append({"period": period, "count": count})

            # Sort by period
            trend_data.sort(key=lambda x: x["period"])

            # Calculate trend direction
            if len(trend_data) >= 2:
                recent_count = sum(item["count"] for item in trend_data[-2:])
                older_count = (
                    sum(item["count"] for item in trend_data[:-2])
                    if len(trend_data) > 2
                    else 1
                )

                trend_direction = (
                    "rising"
                    if recent_count > older_count
                    else "falling" if recent_count < older_count else "stable"
                )
                trend_strength = abs(recent_count - older_count) / max(older_count, 1)
            else:
                trend_direction = "unknown"
                trend_strength = 0

            enhanced["tag_trend_analysis"][tag] = {
                "direction": trend_direction,
                "strength": trend_strength,
                "trend_data": trend_data,
            }

        return enhanced

    def _create_visualization_data(self, patterns):
        """
        Create data structures for pattern visualization.
        """
        # Prepare data for different visualization types
        visualization = {
            "tag_frequency_chart": [],
            "co_occurrence_network": [],
            "tag_timeline": [],
            "source_distribution": [],
        }

        # Tag frequency chart data
        for tag, freq in patterns["tag_frequencies"].items():
            visualization["tag_frequency_chart"].append(
                {
                    "tag": tag,
                    "frequency": freq,
                    "percentage": freq / max(patterns["total_occurrences"], 1) * 100,
                }
            )

        # Co-occurrence network data for graph visualization
        for tag, cooccurrences in patterns["tag_cooccurrences"].items():
            for related_tag, count in cooccurrences.items():
                visualization["co_occurrence_network"].append(
                    {
                        "source": tag,
                        "target": related_tag,
                        "weight": count,
                        "normalized_weight": count
                        / max(patterns["tag_frequencies"].get(tag, 1), 1),
                    }
                )

        # Source distribution analysis
        source_tags = {}
        for tag, analysis in patterns["tag_source_analysis"].items():
            for content_type in analysis["content_types"]:
                if content_type not in source_tags:
                    source_tags[content_type] = []
                source_tags[content_type].append(
                    {"tag": tag, "frequency": analysis["frequency"]}
                )

        visualization["source_distribution"] = source_tags

        return visualization

    def _generate_trending_alerts(self, patterns):
        """
        Generate alerts for trending patterns that need attention.
        """
        alerts = []

        # Alert for rapidly growing tags
        for tag_info in patterns.get("trending_tags", []):
            if tag_info["frequency"] >= 5 and tag_info["diversity_score"] > 0.3:
                alerts.append(
                    {
                        "type": "trending_tag",
                        "severity": "info",
                        "message": f"Tag '{tag_info['tag']}' is trending with {tag_info['frequency']} occurrences across diverse sources",
                        "tag": tag_info["tag"],
                        "data": tag_info,
                    }
                )

        # Alert for tags with high co-occurrence
        for tag, cooccurrences in patterns["tag_cooccurrences"].items():
            if len(cooccurrences) >= 3:  # Tag appears with 3+ other tags frequently
                total_cooccurrence = sum(cooccurrences.values())
                if total_cooccurrence >= 5:
                    alerts.append(
                        {
                            "type": "high_cooccurrence",
                            "severity": "info",
                            "message": f"Tag '{tag}' frequently appears with other tags, suggesting topic clustering",
                            "tag": tag,
                            "related_tags": list(cooccurrences.keys()),
                        }
                    )

        # Alert for potential tag redundancy
        redundant_pairs = []
        for tag1, cooccurrences in patterns["tag_cooccurrences"].items():
            for tag2, count in cooccurrences.items():
                tag1_freq = patterns["tag_frequencies"].get(tag1, 0)
                tag2_freq = patterns["tag_frequencies"].get(tag2, 0)

                # If two tags co-occur in >80% of their appearances, they might be redundant
                if count > 0 and min(tag1_freq, tag2_freq) > 0:
                    cooccurrence_rate = count / min(tag1_freq, tag2_freq)
                    if cooccurrence_rate > 0.8 and count >= 3:
                        redundant_pairs.append((tag1, tag2, cooccurrence_rate))

        for tag1, tag2, rate in redundant_pairs:
            alerts.append(
                {
                    "type": "potential_redundancy",
                    "severity": "warning",
                    "message": f"Tags '{tag1}' and '{tag2}' co-occur in {rate:.1%} of cases - consider consolidation",
                    "tags": [tag1, tag2],
                    "cooccurrence_rate": rate,
                }
            )

        return alerts

    def find_patterns(self, n=3):
        """
        Legacy method for backward compatibility.
        """
        # Use new method but format for old API
        tag_patterns = self.detect_tag_patterns(min_frequency=1)

        # Convert to old format
        top_tags = list(tag_patterns["tag_frequencies"].items())[:n]

        # Get source patterns from temporal analysis
        temporal_patterns = self.metadata_manager.get_temporal_patterns()
        content_type_trends = temporal_patterns.get("content_type_trends", {})

        # Aggregate source counts across time periods
        from collections import Counter

        source_counter = Counter()
        for period_data in content_type_trends.values():
            source_counter.update(period_data)

        top_sources = source_counter.most_common(n)

        return {"top_tags": top_tags, "top_sources": top_sources}

    def get_pattern_insights(self):
        """
        Get high-level insights about content patterns.
        """
        patterns = self.detect_tag_patterns()

        insights = {
            "total_unique_tags": patterns["total_tags"],
            "most_active_tags": patterns["trending_tags"][:3],
            "potential_issues": len(
                [
                    alert
                    for alert in patterns["alerts"]
                    if alert["severity"] == "warning"
                ]
            ),
            "tag_diversity": len(patterns["tag_frequencies"])
            / max(patterns["total_occurrences"], 1),
            "average_tags_per_item": patterns["total_occurrences"]
            / max(len(patterns["tag_frequencies"]), 1),
        }

        return insights

    def clear_cache(self):
        """
        Manually clear the pattern detection cache.
        """
        self._cache.clear()
        self._cache_timestamp = None


# Example usage (for test/demo):
# detector = PatternDetector(metadata_manager)
# patterns = detector.find_patterns(n=5)
# print(patterns)
