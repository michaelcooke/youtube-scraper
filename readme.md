# YouTube Scraper
This is a YouTube web scraper for videos and search queries written for the [Radesky Lab](https://radesky.lab.medicine.umich.edu).

## Getting Started

### Requirements
- Python 3 (developed on 3.9.9)
- [aiohttp](https://docs.aiohttp.org/en/stable/) (developed on 3.8.1)
- [aiohttp-socks](https://github.com/romis2012/aiohttp-socks) (developed on 0.7.1)
- [asyncio](https://docs.python.org/3/library/asyncio.html) (developed on 3.4.3)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) (developed on 4.10.0)
- [pandas](https://pandas.pydata.org) (developed on 1.3.4)

### Import and instantiation
`YouTubeScraper` accepts an optional string to route requests through a SOCKS or HTTP proxy via [aiohttp-socks](https://github.com/romis2012/aiohttp-socks)
```
from youtube_scraper import YoutubeScraper

scraper = YouTubeScraper()
#scraper = YouTubeScraper('socks5://user:password@127.0.0.1:1080')
```

### Getting video metadata
`video_metadata()` accepts a list of YouTube video ids and returns a pandas DataFrame.
```
video_ids = ['dQw4w9WgXcQ', 'ZZ5LpwO-An4', 'J---aiyznGQ']
video_df = await scraper.video_metadata(video_ids)
```

### Getting initially suggested videos from search query
`search_results()` accepts a string search term and returns a list of YouTube video ids initially suggested by YouTube.
```
search_term = 'espresso'
search_results = await scraper.search_results(search_term)
```
