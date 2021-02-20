import argparse
import logging
import random
import string
import time
import uuid

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('N', type=int, help='Number of SET command to generate')
    return parser.parse_args()

def main():
    args = parse_args()

    value = ''.join(random.choices(string.ascii_lowercase, k=256))
    i = 0
    while i < args.N:
        key = uuid.uuid4().hex
        print(f'SET {key} {value}')
        time.sleep(0.05)
        i += 1

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
