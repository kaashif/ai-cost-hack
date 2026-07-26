"""One GPT-5.5 Merge Gateway call per case."""

from costhack.model_strategy import review_with_model
from costhack.schema import Case, ModelClient, Review


def review(case: Case, client: ModelClient) -> Review:
    return review_with_model(case, client, compression="none")
