from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Generator

class BaseStorage(ABC):
    @abstractmethod
    def save_file(self, filename: str, content: bytes, folder: str = "movies") -> str:
        """Saves a file and returns its stored path or URL"""
        pass
        
    @abstractmethod
    def delete_file(self, filepath: str) -> bool:
        """Deletes a file given its path"""
        pass
        
    @abstractmethod
    def file_exists(self, filepath: str) -> bool:
        """Checks if a file exists"""
        pass
        
    @abstractmethod
    def get_file_size(self, filepath: str) -> int:
        """Returns the size of the file in bytes"""
        pass
        
    @abstractmethod
    def get_byte_range(self, filepath: str, start: int, end: int) -> Generator[bytes, None, None]:
        """Yields chunks of bytes between start and end (inclusive)"""
        pass
