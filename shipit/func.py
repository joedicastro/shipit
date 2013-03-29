"""
shipit.func
~~~~~~~~~~~
"""

def unlines(text):
    return text.split('\n')


def lines(line_list):
    return '\n'.join(line_list)


def both(pred1, pred2):
    return lambda x: pred1(x) and pred2(x)

