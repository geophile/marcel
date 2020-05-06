def r_plus(acc, x):
    return x if acc is None else acc + x


def r_times(acc, x):
    return x if acc is None else acc * x


def r_xor(acc, x):
    return x if acc is None else acc ^ x


def r_bit_and(acc, x):
    return x if acc is None else acc & x


def r_bit_or(acc, x):
    return x if acc is None else acc | x


def r_and(acc, x):
    return x if acc is None else acc and x


def r_or(acc, x):
    return x if acc is None else acc or x


def r_max(acc, x):
    return x if acc is None else max(acc, x)


def r_min(acc, x):
    return x if acc is None else min(acc, x)


def r_count(acc, x):
    return 1 if acc is None else acc + 1
