from typing import List, Tuple
from .models import InstructionExample


class DatasetValidator:
    MIN_INSTRUCTION_LENGTH = 3
    MIN_OUTPUT_LENGTH = 5
    MAX_OUTPUT_LENGTH = 8192

    def validate(self, examples: List[InstructionExample]) -> List[Tuple[str, str]]:
        errors: List[Tuple[str, str]] = []
        for ex in examples:
            if len(ex.instruction.strip()) < self.MIN_INSTRUCTION_LENGTH:
                errors.append((ex.id, "instruction_too_short"))
            elif len(ex.output.strip()) < self.MIN_OUTPUT_LENGTH:
                errors.append((ex.id, "output_too_short"))
            elif len(ex.output) > self.MAX_OUTPUT_LENGTH:
                errors.append((ex.id, "output_too_long"))
            elif not ex.instruction.strip():
                errors.append((ex.id, "empty_instruction"))
        return errors

    def quality_estimate(self, example: InstructionExample) -> float:
        score = 1.0
        if len(example.instruction) < 10:
            score -= 0.2
        if len(example.output) < 20:
            score -= 0.2
        if len(example.output) > 2000:
            score -= 0.1
        if example.source == "correction":
            score += 0.1
        if example.metadata.get("rating", 0) >= 4:
            score += 0.1
        return max(0.0, min(1.0, score))
