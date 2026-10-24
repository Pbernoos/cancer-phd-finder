"""Offline configuration checks: dummy inputs only, no external requests."""
from github_runtime import configuration

for env in ({}, {'GITHUB_ACTIONS': 'true'}, {'PHD_OPENAI_API_KEY': 'dummy-not-a-key'}):
    try:
        configuration(env)
        raise AssertionError('Expected configuration to reject missing/incorrect runtime setup')
    except RuntimeError:
        pass
settings = configuration({'GITHUB_ACTIONS': 'true', 'PHD_OPENAI_API_KEY': 'dummy-not-a-key',
                          'OPENAI_API_KEY': 'must-not-use', 'OPENAI_BASE_URL': 'https://invalid.example'})
assert settings['api_key'] == 'dummy-not-a-key'
assert settings['base_url'] == 'https://api.openai.com/v1'
print('5 configuration checks passed; no credentials read and no API calls made.')