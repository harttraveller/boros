print('init alpha', __name__, __package__)
ALPHA = 'alpha-value'


def alpha_func():
    return 'alpha_func'


def lazy_beta():
    from . import beta
    return beta.BETA
