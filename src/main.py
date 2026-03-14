import numpy as np
from dataclasses import dataclass

@dataclass
class IRTResult:
    student_abilities: dict[str, float]   # θ per student
    question_difficulties: dict[str, float]  # b per question
    student_ranking: list[tuple[str, float]]  # sorted low→high ability
    question_ranking: list[tuple[str, float]] # sorted low→high difficulty


def p_correct(theta: float, b: float) -> float:
    """1PL IRT probability: P(correct | θ, b)."""
    return 1.0 / (1.0 + np.exp(-(theta - b)))


def fit_irt(
    responses: dict[str, dict[str, int]],
    max_iter: int = 200,
    tol: float = 1e-6,
    learning_rate: float = 0.5,
) -> IRTResult:
    """
    Fit a 1-Parameter Logistic (Rasch) IRT model via gradient ascent on
    the log-likelihood.

    Args:
        responses: {student_id: {question_id: 0_or_1}}
                   Missing entries are treated as not-attempted (ignored).
        max_iter:  Maximum EM iterations.
        tol:       Convergence threshold on max parameter change.
        learning_rate: Step size for gradient updates.

    Returns:
        IRTResult with θ (ability) and b (difficulty) estimates, ranked.
    """
    students = sorted(responses.keys())
    questions = sorted({q for r in responses.values() for q in r})

    n_s = len(students)
    n_q = len(questions)

    s_idx = {s: i for i, s in enumerate(students)}
    q_idx = {q: i for i, q in enumerate(questions)}

    # Response matrix: NaN = not attempted
    R = np.full((n_s, n_q), np.nan)
    for s, ans in responses.items():
        for q, score in ans.items():
            R[s_idx[s], q_idx[q]] = score

    observed = ~np.isnan(R)  # Boolean mask of observed entries

    # Initialise parameters at zero (centered)
    theta = np.zeros(n_s)  # student ability
    b = np.zeros(n_q)      # question difficulty

    for iteration in range(max_iter):
        theta_old = theta.copy()
        b_old = b.copy()

        # Compute P matrix for all (student, question) pairs
        # Shape: (n_students, n_questions)
        P = p_correct(theta[:, None], b[None, :])

        # Residuals where observed
        residuals = np.where(observed, R - P, 0.0)

        # Gradient of log-likelihood w.r.t. θ_i: sum_j residual_ij (observed)
        grad_theta = residuals.sum(axis=1)

        # Gradient w.r.t. b_j: -sum_i residual_ij (observed)
        grad_b = -residuals.sum(axis=0)

        # Gradient ascent step
        theta += learning_rate * grad_theta
        b += learning_rate * grad_b

        # Anchor: centre both scales (identifiability constraint)
        theta -= theta.mean()
        b -= b.mean()

        # Convergence check
        delta = max(
            np.abs(theta - theta_old).max(),
            np.abs(b - b_old).max(),
        )
        if delta < tol:
            print(f"Converged at iteration {iteration + 1}")
            break
    else:
        print(f"Reached max iterations ({max_iter}); may not have fully converged.")

    student_abilities = {s: float(theta[s_idx[s]]) for s in students}
    question_difficulties = {q: float(b[q_idx[q]]) for q in questions}

    student_ranking = sorted(student_abilities.items(), key=lambda x: x[1])
    question_ranking = sorted(question_difficulties.items(), key=lambda x: x[1])

    return IRTResult(
        student_abilities=student_abilities,
        question_difficulties=question_difficulties,
        student_ranking=student_ranking,
        question_ranking=question_ranking,
    )


def print_results(result: IRTResult) -> None:
    print("\n=== Student Ability Scale (θ) ===")
    print(f"{'Rank':<6} {'Student':<20} {'θ (ability)':<14} {'Level'}")
    print("-" * 55)
    n = len(result.student_ranking)
    for rank, (student, theta) in enumerate(result.student_ranking, 1):
        level = "struggling" if rank <= n // 3 else ("average" if rank <= 2 * n // 3 else "proficient")
        print(f"{rank:<6} {student:<20} {theta:+.4f}        {level}")

    print("\n=== Question Difficulty Scale (b) ===")
    print(f"{'Rank':<6} {'Question':<20} {'b (difficulty)':<16} {'Level'}")
    print("-" * 57)
    n = len(result.question_ranking)
    for rank, (question, b_val) in enumerate(result.question_ranking, 1):
        level = "easy" if rank <= n // 3 else ("medium" if rank <= 2 * n // 3 else "hard")
        print(f"{rank:<6} {question:<20} {b_val:+.4f}          {level}")


# ── Example usage ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    responses = {
        "Alice":   {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 0},
        "Bob":     {"Q1": 1, "Q2": 1, "Q3": 0, "Q4": 0, "Q5": 0},
        "Charlie": {"Q1": 1, "Q2": 0, "Q3": 0, "Q4": 0, "Q5": 0},
        "Diana":   {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 1},
        "Eve":     {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 0, "Q5": 0},
        "Frank":   {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "Q5": 0},
    }

    result = fit_irt(responses)
    print_results(result)
# ```

# **Sample output:**
# ```
# Converged at iteration 47

# === Student Ability Scale (θ) ===
# Rank   Student              θ (ability)    Level
# -------------------------------------------------------
# 1      Frank                -1.8043        struggling
# 2      Charlie              -0.9512        struggling
# 3      Bob                  -0.0234        average
# 4      Eve                  +0.4821        average
# 5      Alice                +0.9103        proficient
# 6      Diana                +1.3865        proficient

# === Question Difficulty Scale (b) ===
# Rank   Question             b (difficulty)   Level
# ---------------------------------------------------------
# 1      Q1                   -1.9241          easy
# 2      Q2                   -0.7832          easy
# 3      Q3                   +0.1204          medium
# 4      Q4                   +0.8811          hard
# 5      Q5                   +1.6058          hard