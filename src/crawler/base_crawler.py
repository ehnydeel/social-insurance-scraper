from abc import ABC
from abc import abstractmethod

class BaseCrawler(ABC):
    @abstractmethod
    def run(self):
        pass