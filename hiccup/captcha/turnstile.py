import aiohttp
from hiccup import SETTINGS


class Turnstile(object):
    def __init__(self, secret_key: str = SETTINGS.captcha_turnstile_secret):
        self.secret_key = secret_key
        self.verify_endpoint = f'{SETTINGS.captcha_turnstile_endpoint}/turnstile/v0/siteverify'

    async def verify(self, challenge_token: str, remote_ip: str = None):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.verify_endpoint, json={
                'secret': self.secret_key,
                'response': challenge_token,
                'remoteip': remote_ip,
            }) as resp:
                if not resp.ok:
                    raise ValueError("Failed to verify challenge token")
                data = await resp.json()
                if 'success' not in data:
                    raise ValueError("Failed to verify challenge token")
                if not data['success']:
                    raise ValueError(f"Failed to verify challenge token: {', '.join(data['error-codes'])}")
                return True
