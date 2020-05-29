import pytest
import numpy as np
from scipy.integrate import quad as sp_quad
import matplotlib.pyplot as plt

from utils.integrate_collection import Monome, Harmonic

from utils.utils import get_log_error
from S3T1_integration.py.integration import (quad,
                                             quad_gauss,
                                             composite_quad,
                                             integrate,
                                             aitken,
                                             moments)


@pytest.mark.parametrize('func', [
    np.sin,
    np.cos,
    np.exp,
    np.sqrt
])
def test_interpolation(func):
    """
    check they are interpolating
    interpolate + integrate via numpy, then compare with quad()
    """
    x0, x1 = 0, 1
    n_nodes = 5

    xs = np.linspace(x0, x1, n_nodes)
    ys = func(xs)

    # numpy
    poly = np.polyfit(xs, ys, deg=n_nodes-1)
    polyint = np.polyint(poly)
    int_v = np.polyval(polyint, x1) - np.polyval(polyint, x0)

    # our
    num_v = quad(func, x0, x1, xs)

    delta = np.abs(int_v - num_v)
    assert delta < 1e-6

    print(f'interpolate+integrate: {int_v:8.3f}, quad: {num_v:8.3f}, delta: {delta:e}')


def test_quad_degree():
    """
    check quadrature degree
    Q: why in some cases x^n integrated perfectly with only n nodes?
    """
    x0, x1 = 0, 1

    max_degree = 7

    for deg in range(1, max_degree):
        p = Monome(deg)
        y0 = p[x0, x1]

        max_node_count = range(1, max_degree+1)

        Y = [quad(p, x0, x1, np.linspace(x0, x1, node_count)) for node_count in max_node_count]
        # Y = [quad(p, x0, x1, x0 + (x1-x0) * np.random.random(node_count)) for node_count in max_node_count]
        accuracy = get_log_error(Y, y0 * np.ones_like(Y))
        accuracy[accuracy > 17] = 17

        # check accuracy is good enough
        for node_count, acc in zip(max_node_count, accuracy):
            if node_count >= deg + 1:
                assert acc > 6

        plt.plot(max_node_count, accuracy, '.:', label=f'x^{deg}')

    plt.legend()
    plt.ylabel('accuracy')
    plt.xlabel('node_count')
    plt.suptitle(f'test quad')
    plt.show()


def test_weighted_quad_degree():
    """
    check weighted quadrature degree
    we compare n-th moment of weight function calculated in two ways:
        - by moments()
        - numerically by quad()
    """
    x0, x1 = 1, 3
    alpha = 0.14
    beta = 0.88

    max_degree = 7
    for deg in range(1, max_degree):
        p = Monome(deg)
        xs = np.linspace(x0, x1, 6)[1:-1]  # 4 points => accuracy degree is 3

        res = quad(p, x0, x1, xs, a=x0, alpha=alpha)
        ans = moments(deg, x0, x1, a=x0, alpha=alpha)[-1]
        d = abs(res - ans)
        print(f'{deg:2}-a: {res:8.3f} vs {ans:8.3f}, delta = {d:e}')
        if deg < len(xs):
            assert d < 1e-6

        res = quad(p, x0, x1, xs, b=x1, beta=beta)
        ans = moments(deg, x0, x1, b=x1, beta=beta)[-1]
        d = abs(res - ans)
        print(f'{deg:2}-b: {res:8.3f} vs {ans:8.3f}, delta = {d:e}')
        if deg < len(xs):
            assert d < 1e-6


def test_quad_gauss_degree():
    """
    check gaussian quadrature degree
    """
    x0, x1 = 0, 1

    max_degree = 8

    for deg in range(2, max_degree):
        p = Monome(deg)
        y0 = p[x0, x1]

        max_node_count = range(2, 6)
        Y = [quad_gauss(p, x0, x1, node_count) for node_count in max_node_count]
        accuracy = get_log_error(Y, y0 * np.ones_like(Y))
        accuracy[accuracy > 17] = 17

        # check accuracy is good enough
        for node_count, acc in zip(max_node_count, accuracy):
            if 2 * node_count >= deg + 1:
                assert acc > 6

        plt.plot(max_node_count, accuracy, '.:', label=f'x^{deg}')

    plt.legend()
    plt.ylabel('accuracy')
    plt.xlabel('node count')
    plt.suptitle(f'test quad gauss')
    plt.show()


@pytest.mark.parametrize('n_nodes', [2, 3, 5])
def test_composite_quad(n_nodes):
    """
    test composite 2-, 3-, 5-node quads
    Q: explain converge speed for each case
    """
    fig, ax = plt.subplots(1, 2)

    x0, x1 = 0, 1
    L = 2
    n_intervals = [L ** q for q in range(0, 8)]

    for i, degree in enumerate((5, 6)):
        p = Monome(degree)
        Y = [composite_quad(p, x0, x1, n_intervals=n, n_nodes=n_nodes) for n in n_intervals]
        accuracy = get_log_error(Y, p[x0, x1] * np.ones_like(Y))
        x = np.log10(n_intervals)

        # check convergence
        ind = np.isfinite(x) & np.isfinite(accuracy)
        k, b = np.polyfit(x[ind], accuracy[ind], 1)
        aitken_degree = aitken(*Y[0:6:2], L ** 2)

        ax[i].plot(x, k*x+b, 'b:', label=f'{k:.2f}*x+{b:.2f}')
        ax[i].plot(x, aitken_degree*x+b, 'm:', label=f'aitken ({aitken_degree:.2f})')
        ax[i].plot(x, accuracy, 'kh', label=f'accuracy for x^{degree}')
        ax[i].set_title(f'{n_nodes}-node CQ for x^{degree}')
        ax[i].set_xlabel('log10(n_intervals)')
        ax[i].set_ylabel('accuracy')
        ax[i].legend()

        if n_nodes < degree:
            assert np.abs(aitken_degree - k) < 0.5, \
                f'Aitken estimation {aitken_degree:.2f} is too far from actual {k:.2f}'

    plt.show()


@pytest.mark.parametrize('v', [2, 3, 5, 6])
def test_composite_quad_degree(v):
    """
    Q: convergence maybe somewhat between 3 and 4, why?
    """
    from .variants import params
    fig, (ax1, ax2) = plt.subplots(1, 2)

    a, b, alpha, beta, f = params(v)
    x0, x1 = a, b
    # a, b = -10, 10
    exact = sp_quad(lambda x: f(x) / (x-a)**alpha / (b-x)**beta, x0, x1)[0]

    # plot weights
    xs = np.linspace(x0, x1, 101)
    ys = 1 / ((xs-a)**alpha * (b-xs)**beta)

    ax1.plot(xs, ys, label='weights')
    ax = list(ax1.axis())
    ax[2] = 0.
    ax1.axis(ax)
    ax1.set_xlabel('x')
    ax1.set_ylabel('p(x)')
    ax1.legend()

    L = 2
    n_intervals = [L ** q for q in range(2, 10)]
    n_nodes = 3
    Y = [composite_quad(f, x0, x1, n_intervals=n, n_nodes=n_nodes,
                        a=a, b=b, alpha=alpha, beta=beta) for n in n_intervals]
    accuracy = get_log_error(Y, exact * np.ones_like(Y))
    x = np.log10(n_intervals)
    k, b = np.polyfit(x, accuracy, 1)
    assert k > 1, 'composite quad did not converge!'
    aitken_degree = aitken(*Y[5:8], L)

    # plot acc
    ax2.plot(x, accuracy, 'kh')
    ax2.plot(x, k*x+b, 'b:', label=f'{k:.2f}*x+{b:.2f}')
    ax2.set_xlabel('log10(n_intervals)')
    ax2.set_ylabel('accuracy')
    ax2.legend()
    fig.suptitle(f'variant #{v} (alpha={alpha:4.2f}, beta={beta:4.2f})\n'
                 f'aitken estimation: {aitken_degree:.2f}')
    plt.show()


def test_gauss_vs_cq():
    """
    check quad_gauss() versus composite_quad() on the same number of function evaluations
    """
    x0, x1 = 0, np.pi/2

    p = Harmonic(0, 1)
    y0 = p[x0, x1]

    n_nodes = 2
    Y_gauss = []
    Y_cquad = []

    n_intervals = np.arange(1, 256, 5)
    for n in n_intervals:
        n_evals = n * n_nodes
        Y_gauss.append(quad_gauss(p, x0, x1, n_evals))
        Y_cquad.append(composite_quad(p, x0, x1, n, n_nodes))

    accuracy_gauss = get_log_error(Y_gauss, y0 * np.ones_like(Y_gauss))
    accuracy_gauss[accuracy_gauss > 17] = 17

    accuracy_cquad = get_log_error(Y_cquad, y0 * np.ones_like(Y_cquad))
    accuracy_cquad[accuracy_cquad > 17] = 17

    plt.plot(np.log10(n_intervals), accuracy_gauss, '.:', label=f'gauss')
    plt.plot(np.log10(n_intervals), accuracy_cquad, '.:', label=f'2-node CQ')

    plt.legend()
    plt.ylabel('accuracy')
    plt.xlabel('log10(n_evals)')
    plt.suptitle(f'test gauss vs CQ')
    plt.show()


def test_integrate():
    """
    integrate with a given tolerance
    """
    p = Harmonic(1, 0)
    x0, x1 = 0, np.pi

    for tol in 10. ** np.arange(-9, -2):
        s, err = integrate(p, x0, x1, tol=tol)

        print(f'Check for tol {tol:.2e}: res = {s-err:.6f} .. {s:.6f} .. {s+err:.6f}')

        assert err >= 0,                            'estimated error should be >= 0'
        assert np.abs(p[x0, x1] - s) <= 1.1*err,    'actual error should be <= estimated error + 10%'
        assert np.abs(p[x0, x1] - s) <= tol,        'actual error should be <= tolerance'
