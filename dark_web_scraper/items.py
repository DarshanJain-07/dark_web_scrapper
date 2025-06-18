# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ScrapedDataItem(scrapy.Item):
    # The URL of the page
    url = scrapy.Field()
    # The processed text content from the page
    text_content = scrapy.Field()
    # The raw HTML of the page, in case we need it later
    html_content = scrapy.Field()
    # The timestamp of when the item was scraped
    timestamp = scrapy.Field() 