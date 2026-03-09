import requests


class APIClient:

    def __init__(self, base_url, user, key):

        self.base_url = base_url
        self.user = user
        self.key = key

    def get(self, endpoint, params=None):

        response = requests.get(
            f"{self.base_url}/{endpoint}",
            params=params,
            auth=(self.user, self.key),
            timeout=20
        )

        response.raise_for_status()

        return response.json()