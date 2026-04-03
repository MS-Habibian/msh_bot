import aiohttp


async def get_file_size_from_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return int(response.headers.get("Content-Length", 0))
