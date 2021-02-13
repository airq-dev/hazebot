import json
import random


def main():
    path = '../app/tests/fixtures/purpleair/purpleair.json'
    with open(path, 'r') as f:
        data = json.load(f)
    data['fields'].append('humidity')
    for d in data['data']:
        d.append(random.randint(0, 100))
    with open(path, 'w') as f:
        json.dump(data, f)


if __name__ == '__main__':
    main()