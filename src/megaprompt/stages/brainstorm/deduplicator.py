"""Deduplication stage implementation."""

from megaprompt.schemas.brainstorm import ProjectIdea


class Deduplicator:
    """Removes duplicate or too-similar ideas."""

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize deduplicator.

        Args:
            similarity_threshold: Threshold for considering ideas similar (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, ideas: list[ProjectIdea]) -> list[ProjectIdea]:
        """
        Remove duplicate or too-similar ideas.

        Args:
            ideas: List of ideas to deduplicate

        Returns:
            List of deduplicated ideas
        """
        if len(ideas) <= 1:
            return ideas

        unique_ideas: list[ProjectIdea] = []
        seen_signatures: set[str] = set()

        for idea in ideas:
            signature = self._create_signature(idea)
            
            # Check if we've seen a similar signature
            is_duplicate = False
            for seen_sig in seen_signatures:
                similarity = self._calculate_similarity(signature, seen_sig)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_ideas.append(idea)
                seen_signatures.add(signature)

        return unique_ideas

    def _create_signature(self, idea: ProjectIdea) -> str:
        """
        Create a signature string for an idea based on core characteristics.

        Args:
            idea: The idea to create signature for

        Returns:
            Signature string
        """
        # Combine core_loop, key_systems, and unique_twist
        core_text = " ".join(idea.core_loop).lower()
        systems_text = " ".join(idea.key_systems).lower()
        twist_text = idea.unique_twist.lower()
        
        # Normalize: remove common words, normalize spacing
        signature_parts = [core_text, systems_text, twist_text]
        signature = " | ".join(signature_parts)
        
        return signature

    def _calculate_similarity(self, sig1: str, sig2: str) -> float:
        """
        Calculate similarity between two signatures.

        Args:
            sig1: First signature
            sig2: Second signature

        Returns:
            Similarity score (0.0-1.0)
        """
        # Simple word overlap similarity
        words1 = set(sig1.split())
        words2 = set(sig2.split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        return intersection / union

