class RecallEngine:
    def __init__(self, metadata_manager, config=None):
        self.metadata_manager = metadata_manager
        self.config = config or {}

    def get_items_for_review(self, limit=10):
        """
        Get optimally scheduled review items using enhanced MetadataManager methods.
        Enhanced with difficulty adjustment and progress tracking.
        """
        # Use the new get_recall_items method which has sophisticated spaced repetition
        recall_items = self.metadata_manager.get_recall_items(limit)

        # Enhance with difficulty adjustment and user feedback
        enhanced_items = []
        for item in recall_items:
            review_data = self._get_review_data(item)
            enhanced_items.append(
                {
                    "metadata": item,
                    "review_data": review_data,
                    "difficulty_score": self._calculate_difficulty_score(
                        item, review_data
                    ),
                    "review_urgency": self._calculate_urgency(item, review_data),
                }
            )

        # Sort by urgency (highest first)
        enhanced_items.sort(key=lambda x: x["review_urgency"], reverse=True)

        return enhanced_items

    def _get_review_data(self, metadata):
        """
        Extract review-specific data from metadata.
        """
        return {
            "last_reviewed": (
                metadata.type_specific.get("last_reviewed")
                if metadata.type_specific
                else None
            ),
            "review_count": (
                metadata.type_specific.get("review_count", 0)
                if metadata.type_specific
                else 0
            ),
            "success_rate": (
                metadata.type_specific.get("review_success_rate", 1.0)
                if metadata.type_specific
                else 1.0
            ),
            "difficulty_rating": (
                metadata.type_specific.get("difficulty_rating", 3)
                if metadata.type_specific
                else 3
            ),  # 1-5 scale
        }

    def _calculate_difficulty_score(self, metadata, review_data):
        """
        Calculate difficulty score based on content characteristics and review history.
        """
        difficulty = 1.0

        # Base difficulty from user rating
        difficulty += (review_data["difficulty_rating"] - 3) * 0.2  # Normalize around 3

        # Content complexity factors
        if len(metadata.tags) > 5:  # Highly tagged content might be more complex
            difficulty += 0.3

        # Content type difficulty
        type_difficulty = {
            "article": 1.0,
            "youtube": 0.8,
            "podcast": 0.9,
            "instapaper": 1.1,
        }
        difficulty *= type_difficulty.get(metadata.content_type.value, 1.0)

        # Historical performance
        if review_data["success_rate"] < 0.7:  # Poor performance = higher difficulty
            difficulty += 0.4
        elif review_data["success_rate"] > 0.9:  # Good performance = lower difficulty
            difficulty -= 0.2

        return max(difficulty, 0.1)  # Minimum difficulty

    def _calculate_urgency(self, metadata, review_data):
        """
        Calculate review urgency based on spaced repetition principles.
        """
        from datetime import datetime, timedelta

        urgency = 1.0

        # Time-based urgency
        if review_data["last_reviewed"]:
            try:
                last_reviewed = datetime.fromisoformat(
                    review_data["last_reviewed"].replace("Z", "+00:00")
                )
                days_since_review = (datetime.now() - last_reviewed).days

                # Exponential urgency growth based on spaced repetition intervals
                review_intervals = [1, 3, 7, 14, 30, 60, 120]
                expected_interval = review_intervals[
                    min(review_data["review_count"], len(review_intervals) - 1)
                ]

                if days_since_review > expected_interval:
                    overdue_factor = days_since_review / expected_interval
                    urgency *= 1.0 + overdue_factor

            except (ValueError, AttributeError):
                pass
        else:
            # Never reviewed = high urgency
            urgency += 1.0

        # Difficulty affects urgency (harder items need more frequent review)
        difficulty_score = self._calculate_difficulty_score(metadata, review_data)
        urgency *= 1.0 + difficulty_score * 0.2

        # Success rate affects urgency (poor performance = higher urgency)
        if review_data["success_rate"] < 0.8:
            urgency *= 1.3

        return urgency

    def mark_reviewed(self, content_metadata, success=True, difficulty_rating=None):
        """
        Mark a content item as reviewed with enhanced feedback tracking.
        """
        from datetime import datetime

        if (
            not hasattr(content_metadata, "type_specific")
            or content_metadata.type_specific is None
        ):
            content_metadata.type_specific = {}

        # Update review timestamp and count
        content_metadata.type_specific["last_reviewed"] = datetime.now().isoformat()
        review_count = content_metadata.type_specific.get("review_count", 0) + 1
        content_metadata.type_specific["review_count"] = review_count

        # Update success rate (exponential moving average)
        current_success_rate = content_metadata.type_specific.get(
            "review_success_rate", 1.0
        )
        alpha = 0.3  # Learning rate
        new_success_rate = (
            alpha * (1.0 if success else 0.0) + (1 - alpha) * current_success_rate
        )
        content_metadata.type_specific["review_success_rate"] = new_success_rate

        # Update difficulty rating if provided
        if difficulty_rating is not None:
            content_metadata.type_specific["difficulty_rating"] = max(
                1, min(5, difficulty_rating)
            )

        # Calculate next review date based on performance
        next_review_interval = self._calculate_next_interval(
            review_count, success, new_success_rate
        )
        next_review_date = datetime.now() + timedelta(days=next_review_interval)
        content_metadata.type_specific["next_review_date"] = (
            next_review_date.isoformat()
        )

        self.metadata_manager.save_metadata(content_metadata)

    def _calculate_next_interval(self, review_count, success, success_rate):
        """
        Calculate the next review interval based on spaced repetition algorithms.
        """
        base_intervals = [1, 3, 7, 14, 30, 60, 120, 240]  # days

        # Get base interval
        base_interval = base_intervals[min(review_count - 1, len(base_intervals) - 1)]

        # Adjust based on success
        if success:
            # Success = increase interval
            if success_rate > 0.9:
                multiplier = 1.5  # High success rate = longer intervals
            elif success_rate > 0.7:
                multiplier = 1.2
            else:
                multiplier = 1.0  # Normal progression
        else:
            # Failure = decrease interval significantly
            multiplier = 0.3

        return max(1, int(base_interval * multiplier))

    def get_review_analytics(self):
        """
        Get analytics about review performance and patterns.
        """
        all_items = self.metadata_manager.get_all_metadata()

        total_items = len(all_items)
        reviewed_items = []
        never_reviewed = 0

        for item in all_items:
            if item.type_specific and item.type_specific.get("last_reviewed"):
                reviewed_items.append(item)
            else:
                never_reviewed += 1

        if not reviewed_items:
            return {
                "total_items": total_items,
                "never_reviewed": never_reviewed,
                "review_completion_rate": 0,
                "average_success_rate": 0,
                "average_review_count": 0,
            }

        # Calculate statistics
        total_reviews = sum(
            item.type_specific.get("review_count", 0) for item in reviewed_items
        )
        total_success_rate = sum(
            item.type_specific.get("review_success_rate", 1.0)
            for item in reviewed_items
        )

        return {
            "total_items": total_items,
            "reviewed_items": len(reviewed_items),
            "never_reviewed": never_reviewed,
            "review_completion_rate": len(reviewed_items) / total_items,
            "average_success_rate": total_success_rate / len(reviewed_items),
            "average_review_count": total_reviews / len(reviewed_items),
            "items_due_today": len(self.get_items_for_review(100)),
        }

    def schedule_spaced_repetition(self, n=5):
        """
        Legacy method for backward compatibility.
        """
        items = self.get_items_for_review(n)
        return [item["metadata"] for item in items]


# Example usage (for test/demo):
# engine = RecallEngine(metadata_manager)
# due = engine.schedule_spaced_repetition(n=3)
# for item in due:
#     print(item.title, item.type_specific.get('last_reviewed'))
#     engine.mark_reviewed(item)
