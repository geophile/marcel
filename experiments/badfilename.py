import pathlib

dir = pathlib.Path('/home/jao/teaching/tufts/115/2019s/assignments/a3/plagiarism')

s = set()
good = 0
bad = 0
for f in dir.iterdir():
    try:
        print(f'{type(f)}: {f}')
        good += 1
    except UnicodeEncodeError:
        print('Bad filename')
        bad += 1
    s.add(f)
print(f'good: {good}')
print(f'bad: {bad}')
print(f'total: {good + bad}')
print(f's: {len(s)}')
