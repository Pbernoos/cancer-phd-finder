"""Explicit external GitHub Actions runtime; never used by ARIA model calls.

Uses only the repository's dedicated OpenAI secret, not ARIA/W&B credentials.
There is no automatic fallback between providers.
"""
import os
from openai import OpenAI


def configuration(env=None):
    env = os.environ if env is None else env
    if env.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('github-openai mode runs only in GitHub Actions. Use the default W&B proxy in ARIA.')
    key = env.get('PHD_OPENAI_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Missing repository secret PHD_OPENAI_API_KEY. Add your own OpenAI API key in repository Settings > Secrets and variables > Actions.')
    return {'api_key': key, 'base_url': 'https://api.openai.com/v1',
            'timeout': 100, 'max_retries': 0}


def client():
    return OpenAI(**configuration())


if __name__ == '__main__':
    configuration()
    print('Dedicated GitHub credential is configured. No API request was made; access and billing are not yet verified.')