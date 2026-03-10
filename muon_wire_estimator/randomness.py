"""
Deterministic random-number helpers for Level 2 stochastic simulation.

This module centralizes all RNG handling so event-by-event simulation remains:

- reproducible for a fixed seed
- lightweight
- standard-library-only
- easy to reason about

It wraps Python's ``random.Random`` with a small utility class and provides
commonly needed stochastic primitives for the estimator:

- Poisson sampling
- binomial sampling
- exponential survival tests
- gamma-distributed gain fluctuations
- simple helper methods for arrays of repeated samples

The implementation is intentionally pragmatic rather than maximally optimized.
Typical use for this project is O(10^2-10^5) events, which is well within the
range of straightforward standard-library methods.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass(slots=True)
class SeededRNG:
    """
    Thin deterministic wrapper around :class:`random.Random`.

    Parameters
    ----------
    seed:
        Integer seed controlling reproducibility.

    Notes
    -----
    A dedicated wrapper gives the project a stable place to extend RNG behavior
    later without exposing raw ``random.Random`` everywhere.
    """

    seed: int
    _generator: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int):
            raise TypeError(f"seed must be an int, got {type(self.seed).__name__}.")
        self._generator = random.Random(self.seed)

        
    @property
    def generator(self) -> random.Random:
        """Return the underlying ``random.Random`` instance."""
        return self._generator

    def uniform(self, a: float = 0.0, b: float = 1.0) -> float:
        """Sample uniformly on [a, b]."""
        if b < a:
            raise ValueError(f"uniform requires b >= a, got a={a!r}, b={b!r}.")
        return self._generator.uniform(a, b)

    def random(self) -> float:
        """Sample uniformly on [0, 1)."""
        return self._generator.random()

    def randint(self, a: int, b: int) -> int:
        """Sample an integer uniformly from the closed interval [a, b]."""
        if b < a:
            raise ValueError(f"randint requires b >= a, got a={a!r}, b={b!r}.")
        return self._generator.randint(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        """Sample from a Gaussian distribution."""
        if sigma < 0.0:
            raise ValueError(f"sigma must be >= 0, got {sigma!r}.")
        return self._generator.gauss(mu, sigma)

    def expovariate(self, lambd: float) -> float:
        """Sample from an exponential distribution with rate ``lambd``."""
        if lambd <= 0.0:
            raise ValueError(f"lambd must be > 0, got {lambd!r}.")
        return self._generator.expovariate(lambd)

    def gammavariate(self, alpha: float, beta: float) -> float:
        """
        Sample from a Gamma distribution with shape ``alpha`` and scale ``beta``.
        """
        if alpha <= 0.0:
            raise ValueError(f"alpha must be > 0, got {alpha!r}.")
        if beta <= 0.0:
            raise ValueError(f"beta must be > 0, got {beta!r}.")
        return self._generator.gammavariate(alpha, beta)

    def poisson(self, mean: float) -> int:
        """
        Sample from a Poisson distribution with mean ``mean``.

        Strategy
        --------
        - For small/moderate mean, use Knuth's exact multiplicative algorithm.
        - For larger mean, use a Gaussian approximation with rounding and clamp
          to zero. This is sufficient for the estimator's engineering purpose.
        """
        return sample_poisson(self._generator, mean)

    def binomial(self, n: int, p: float) -> int:
        """Sample from a Binomial distribution."""
        return sample_binomial(self._generator, n, p)

    def bernoulli(self, p: float) -> bool:
        """Sample a Bernoulli event."""
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p must be in [0, 1], got {p!r}.")
        return self._generator.random() < p

    def choice_index_from_weights(self, weights: list[float]) -> int:
        """
        Sample an index from non-negative weights.

        Parameters
        ----------
        weights:
            Sequence of non-negative weights. At least one weight must be > 0.
        """
        if not weights:
            raise ValueError("weights must be non-empty.")
        if any(weight < 0.0 for weight in weights):
            raise ValueError("weights must all be >= 0.")
        total = sum(weights)
        if total <= 0.0:
            raise ValueError("At least one weight must be > 0.")
        draw = self._generator.random() * total
        cumulative = 0.0
        for index, weight in enumerate(weights):
            cumulative += weight
            if draw <= cumulative:
                return index
        return len(weights) - 1


def make_rng(seed: int) -> SeededRNG:
    """
    Construct a deterministic RNG wrapper.
    """
    return SeededRNG(seed=seed)


def sample_poisson(rng: random.Random, mean: float) -> int:
    """
    Sample a Poisson random variable with mean ``mean``.

    Parameters
    ----------
    rng:
        Source random generator.
    mean:
        Poisson mean parameter, must be >= 0.

    Returns
    -------
    int
        Sampled non-negative integer.
    """
    if mean < 0.0:
        raise ValueError(f"mean must be >= 0, got {mean!r}.")
    if mean == 0.0:
        return 0

    if mean < 50.0:
        limit = math.exp(-mean)
        product = 1.0
        count = 0
        while product > limit:
            count += 1
            product *= rng.random()
        return count - 1

    # Gaussian approximation for large mean
    sample = int(round(rng.gauss(mean, math.sqrt(mean))))
    return max(sample, 0)


def sample_binomial(rng: random.Random, n: int, p: float) -> int:
    """
    Sample a Binomial random variable.

    Parameters
    ----------
    rng:
        Source random generator.
    n:
        Number of trials, must be >= 0.
    p:
        Success probability in [0, 1].
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n!r}.")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must be in [0, 1], got {p!r}.")
    if n == 0 or p == 0.0:
        return 0
    if p == 1.0:
        return n

    successes = 0
    for _ in range(n):
        if rng.random() < p:
            successes += 1
    return successes


def sample_exponential_survival(
    rng: random.Random,
    *,
    survival_fraction: float,
    n_trials: int,
) -> int:
    """
    Sample surviving objects from an externally computed survival fraction.

    This is effectively a binomial draw but named for clarity when the survival
    probability came from an exponential attachment law.
    """
    return sample_binomial(rng, n_trials, survival_fraction)


def sample_gamma_gain(
    rng: random.Random,
    *,
    mean_gain: float,
    shape: float,
) -> float:
    """
    Sample a stochastic gas gain using a Gamma distribution.

    Parameterization
    ----------------
    For a Gamma(shape=k, scale=theta), mean = k * theta.
    Therefore theta = mean_gain / shape.

    This gives a convenient one-parameter fluctuation model:
    - large shape -> narrower fluctuations
    - shape մոտ 1 -> exponential-like fluctuations

    Returns
    -------
    float
        Non-negative sampled gain.
    """
    if mean_gain < 0.0:
        raise ValueError(f"mean_gain must be >= 0, got {mean_gain!r}.")
    if shape <= 0.0:
        raise ValueError(f"shape must be > 0, got {shape!r}.")
    if mean_gain == 0.0:
        return 0.0
    scale = mean_gain / shape
    return rng.gammavariate(shape, scale)


def sample_nonnegative_gaussian(
    rng: random.Random,
    *,
    mean: float,
    sigma: float,
) -> float:
    """
    Sample from a Gaussian and clamp at zero.

    Useful for large-mean approximations where negativity is unphysical.
    """
    if sigma < 0.0:
        raise ValueError(f"sigma must be >= 0, got {sigma!r}.")
    if mean < 0.0:
        raise ValueError(f"mean must be >= 0, got {mean!r}.")
    if sigma == 0.0:
        return mean
    return max(rng.gauss(mean, sigma), 0.0)


def repeated_poisson_samples(
    rng: SeededRNG,
    *,
    mean: float,
    n_samples: int,
) -> list[int]:
    """
    Draw repeated Poisson samples.
    """
    if n_samples < 0:
        raise ValueError(f"n_samples must be >= 0, got {n_samples!r}.")
    return [rng.poisson(mean) for _ in range(n_samples)]


def repeated_gamma_gain_samples(
    rng: SeededRNG,
    *,
    mean_gain: float,
    shape: float,
    n_samples: int,
) -> list[float]:
    """
    Draw repeated Gamma gain samples.
    """
    if n_samples < 0:
        raise ValueError(f"n_samples must be >= 0, got {n_samples!r}.")
    return [
        sample_gamma_gain(rng.generator, mean_gain=mean_gain, shape=shape)
        for _ in range(n_samples)
    ]


__all__ = [
    "SeededRNG",
    "make_rng",
    "repeated_gamma_gain_samples",
    "repeated_poisson_samples",
    "sample_binomial",
    "sample_exponential_survival",
    "sample_gamma_gain",
    "sample_nonnegative_gaussian",
    "sample_poisson",
]