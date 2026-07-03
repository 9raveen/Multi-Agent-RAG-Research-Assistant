# benchmark_dataset.py
# RAGAS benchmark questions for the gradient descent document.
# Each item: question, ground_truth, and a `type` tag for reporting/filtering.
#
# Types:
#   factual_single_hop   — answer found in one chunk, no synthesis needed
#   factual_multi_hop    — requires combining info across 2+ chunks
#   table_lookup         — answer requires reading table-structured content
#   negative_out_of_scope — question NOT answerable from this document
#                           (expects "not found" / refusal, tests contamination guard)
#   comparative           — requires contrasting two or more concepts

BENCHMARK = [
    # ── Batch 1: original 5, single-hop factual (validated clean) ──
    {
        "question": "What is gradient descent?",
        "ground_truth": "Gradient descent is a fundamental optimization algorithm in machine learning used to minimize a function by iteratively moving towards the minimum, in the direction of steepest descent.",
        "type": "factual_single_hop",
    },
    {
        "question": "What is batch gradient descent?",
        "ground_truth": "Batch gradient descent is a variant of gradient descent where the entire dataset is used to compute the gradient of the loss function with respect to the parameters in each iteration.",
        "type": "factual_single_hop",
    },
    {
        "question": "What is stochastic gradient descent?",
        "ground_truth": "Stochastic gradient descent (SGD) is a variant of gradient descent where the model parameters are updated using the gradient of the loss function with respect to a single training example at each iteration.",
        "type": "factual_single_hop",
    },
    {
        "question": "What is mini-batch gradient descent?",
        "ground_truth": "Mini-batch gradient descent is a compromise between batch and stochastic gradient descent, updating parameters using a small, random subset (mini-batch) of the training data at each iteration.",
        "type": "factual_single_hop",
    },
    {
        "question": "What is the update rule for batch gradient descent?",
        "ground_truth": "The update rule is theta = theta - eta * gradient(J(theta)), where theta is the model parameters, eta is the learning rate, and gradient(J(theta)) is the gradient of the loss function with respect to theta.",
        "type": "factual_single_hop",
    },

    # ── Batch 2: comparative + multi-hop (new) ──
    {
        "question": "What is the main tradeoff between batch gradient descent and stochastic gradient descent?",
        "ground_truth": "Batch gradient descent gives stable, accurate gradient estimates but is computationally expensive per step since it uses the whole dataset, while stochastic gradient descent is much faster per update but noisier and less stable since it uses only one example at a time.",
        "type": "comparative",
    },
    {
        "question": "Why might mini-batch gradient descent be preferred over both batch and stochastic gradient descent in practice?",
        "ground_truth": "Mini-batch gradient descent balances the stability of batch gradient descent with the computational efficiency of stochastic gradient descent, and it also enables vectorized/parallel computation on hardware like GPUs.",
        "type": "factual_multi_hop",
    },
    {
        "question": "How does the choice of learning rate affect convergence in gradient descent?",
        "ground_truth": "A learning rate that is too high can cause the algorithm to overshoot the minimum or diverge, while a learning rate that is too low results in slow convergence, requiring many more iterations to reach the minimum.",
        "type": "factual_multi_hop",
    },

    # ── Batch 3: negative / out-of-scope (tests contamination guard) ──
    {
        "question": "What is the capital of France?",
        "ground_truth": "This document does not contain information about geography or world capitals; it covers gradient descent and its variants.",
        "type": "negative_out_of_scope",
    },
    {
        "question": "What model architecture does this document recommend for image classification?",
        "ground_truth": "This document does not discuss image classification or specific model architectures; it focuses on gradient descent optimization algorithms.",
        "type": "negative_out_of_scope",
    },
]