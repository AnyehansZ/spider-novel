class BaseCrawler:
    def __init__(self, novel_name, output_folder, base_url, start_url):
        self.novel_name = novel_name
        self.output_folder = output_folder
        self.base_url = base_url
        self.start_url = start_url

    def run_crawler(self):
        """Starts or resumes the crawling process."""
        raise NotImplementedError("Crawlers must implement run_crawler()")

    def check_and_fix_missing(self):
        """Checks for missing chapter files and attempts to download them."""
        raise NotImplementedError("Crawlers must implement check_and_fix_missing()")