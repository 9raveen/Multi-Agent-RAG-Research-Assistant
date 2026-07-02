# benchmark_dataset.py
# Ground truth question/answer pairs for RAGAS evaluation.
# Each entry: a question your ingested documents should be able to answer,
# plus a hand-verified ground_truth answer used to score Context Recall
# and compare against generated answers.

BENCHMARK = [
    {
        "question": "What is gradient descent?",
        "ground_truth": "Gradient descent is a fundamental optimization algorithm in machine learning used to minimize functions by iteratively moving towards the minimum. It works by finding the steepest downward direction and taking small steps in that direction repeatedly.",
    },
    {
        "question": "What is batch gradient descent?",
        "ground_truth": "Batch Gradient Descent is a variant of gradient descent where the entire dataset is used to compute the gradient of the loss function in each iteration, calculating the average gradient across all training examples before updating parameters.",
    },
    {
        "question": "What is stochastic gradient descent?",
        "ground_truth": "Stochastic Gradient Descent (SGD) updates model parameters using the gradient of the loss function with respect to a single training example at each iteration, rather than the entire dataset, leading to more frequent updates and faster convergence than batch gradient descent.",
    },
    {
        "question": "What is mini-batch gradient descent?",
        "ground_truth": "Mini-Batch Gradient Descent is a compromise between Batch Gradient Descent and Stochastic Gradient Descent. It updates model parameters using a small, random subset of the training data (a mini-batch) rather than the entire dataset or a single example.",
    },
    {
        "question": "What is the update rule for batch gradient descent?",
        "ground_truth": "The update rule for batch gradient descent is: theta = theta - eta * gradient of J(theta), where theta represents the model parameters, eta is the learning rate, and the gradient of J(theta) is the gradient of the loss function with respect to theta.",
    },
    # Add 5-10 more covering your actual ingested content.
    # Keep ground_truth answers factual and traceable to a specific page —
    # this makes it easy to spot-check RAGAS scores against the source later.
]